#!/usr/bin/env python3
"""content/hafta/H*.json dosyalarını doğrular ve uygulamanın okuduğu
netlify/functions/lib/content.mjs dosyasını üretir.

    python3 automation/icerik_derle.py          # derle
    python3 automation/icerik_derle.py --kontrol # sadece doğrula
"""
import datetime as dt, glob, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPTS = ["uretim", "lojistik", "kalite", "bakim", "dial"]
DEPT_TR = {"uretim": "Üretim", "lojistik": "Lojistik", "kalite": "Kalite", "bakim": "Bakım", "dial": "Dial Lab"}


def takvim():
    return json.load(open(os.path.join(ROOT, "content", "takvim.json"), encoding="utf-8"))


def hafta_dosyalari():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "content", "hafta", "H*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        out[int(d["hafta"])] = d
    return out


def dogrula(w, d):
    hatalar = []
    for dk, v in d.get("departmanlar", {}).items():
        if dk not in DEPTS:
            hatalar.append(f"H{w}: bilinmeyen departman '{dk}'"); continue
        for lang in ("tr", "en"):
            x = v.get(lang)
            if not x:
                if lang == "tr": hatalar.append(f"H{w} {dk}: tr içeriği yok")
                continue
            for alan in ("t", "metin", "rules", "key", "tf", "mc", "classic"):
                if not x.get(alan): hatalar.append(f"H{w} {dk}/{lang}: '{alan}' boş")
            if len(x.get("tf", [])) + len(x.get("mc", [])) < 5: hatalar.append(f"H{w} {dk}/{lang}: haftalık quiz için en az 5 D/Y+ÇS soru gerekli")
            for i, q in enumerate(x.get("mc", [])):
                if not (isinstance(q.get("a"), int) and 0 <= q["a"] < len(q.get("opts", []))): hatalar.append(f"H{w} {dk}/{lang}: ÇS {i+1} doğru şık hatalı")
            for i, q in enumerate(x.get("tf", [])):
                if not isinstance(q.get("a"), bool): hatalar.append(f"H{w} {dk}/{lang}: D/Y {i+1} cevabı true/false olmalı")
        if v.get("en") and v.get("tr"):
            for k in ("tf", "mc", "classic"):
                if len(v["en"].get(k, [])) != len(v["tr"].get(k, [])): hatalar.append(f"H{w} {dk}: en/tr {k} soru sayıları farklı")
    return hatalar


def dongu_listesi(T, haftalar):
    h0 = T["baslangic_hafta"]; d0 = dt.date.fromisoformat(T["baslangic_tarih"]); n = T["egitim_hafta_sayisi"]; L = n + 1
    gruplar = {}
    for w in sorted(haftalar):
        if w < T.get("otomatik_baslangic", h0): continue
        if (w - h0) % L == n: continue  # tekrar haftası
        base = w - (w - h0) % L
        gruplar.setdefault(base, []).append(w)
    cikti = []
    for base, ws in sorted(gruplar.items()):
        date = (d0 + dt.timedelta(days=7 * (base - h0))).isoformat()
        lang_parts = {}
        for lang in ("tr", "en"):
            subjects, content, pools = {}, {}, {}
            for dk in DEPTS:
                subjects[dk] = []; content[dk] = {}; pools[dk] = {"tf": [], "mc": [], "classic": []}
                for w in ws:
                    v = haftalar[w].get("departmanlar", {}).get(dk)
                    if not v: continue
                    x = v.get(lang) or v["tr"]
                    subjects[dk].append({"w": w, "t": x["t"]})
                    ek = ("\n\n## Key rules\n" if lang == "en" else "\n\n## Ana kurallar\n") + "\n".join("- " + r for r in x["rules"]) + ("\n\n## Remember\n" if lang == "en" else "\n\n## Unutmayın\n") + x["key"]
                    content[dk][str(w)] = x["metin"].rstrip() + ek
                    for i, q in enumerate(x["tf"]): pools[dk]["tf"].append({"id": f"t{w}{dk[:2]}{i}", "q": q["q"], "a": bool(q["a"]), "w": w})
                    for i, q in enumerate(x["mc"]): pools[dk]["mc"].append({"id": f"m{w}{dk[:2]}{i}", "q": q["q"], "opts": q["opts"], "a": q["a"], "w": w})
                    for i, q in enumerate(x["classic"]): pools[dk]["classic"].append({"id": f"c{w}{dk[:2]}{i}", "q": q["q"], "key": q["key"], "w": w})
            pools["ortak"] = {"tf": [], "mc": [], "classic": []}
            lang_parts[lang] = {"subjects": subjects, "content": content, "pools": pools}
        son = base + n - 1
        cyc = {"id": f"auto_H{base}", "base": base, "weeks": ws, "weeksPlan": list(range(base, base + n)), "date": date,
               "title": f"Hafta {base}–{son} Toolbox", **lang_parts["tr"],
               "i18n": {"en": {"title": f"Weeks {base}–{son} Toolbox", **lang_parts["en"]}}}
        cyc["hash"] = hashlib.sha1(json.dumps(cyc, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        cikti.append(cyc)
    return cikti


def main():
    T = takvim(); H = hafta_dosyalari()
    hatalar = [h for w, d in H.items() for h in dogrula(w, d)]
    if hatalar:
        print("\n".join(hatalar)); sys.exit(1)
    cycles = dongu_listesi(T, H)
    if "--kontrol" in sys.argv:
        print(json.dumps([{"id": c["id"], "haftalar": c["weeks"], "tarih": c["date"]} for c in cycles], ensure_ascii=False)); return
    payload = {"takvim": {k: T[k] for k in ("baslangic_hafta", "baslangic_tarih", "egitim_hafta_sayisi")}, "cycles": cycles}
    payload["hash"] = hashlib.sha1("".join(c["hash"] for c in cycles).encode()).hexdigest()[:16]
    out = os.path.join(ROOT, "netlify", "functions", "lib", "content.mjs")
    with open(out, "w", encoding="utf-8") as f:
        f.write("// OTOMATİK ÜRETİLİR — elle düzenlemeyin. Kaynak: content/hafta/*.json (automation/icerik_derle.py)\n")
        f.write("export default " + json.dumps(payload, ensure_ascii=False) + ";\n")
    print(json.dumps({"dosya": out, "donemler": [{"id": c["id"], "haftalar": c["weeks"], "tarih": c["date"]} for c in cycles]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
