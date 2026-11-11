#!/usr/bin/env python3
"""Haftalık eğitim içeriklerinden (content/hafta/H*.json) Döhler toolbox eğitim föyü (A4 yatay PDF) üretir.

    python3 automation/egitim_pdf.py --hafta 39 [--dil tr|en] [--cikti klasor]

Görsel: content/gorsel/H{hafta}_{departman}.jpg|png varsa o fotoğraf kullanılır; yoksa konuya göre
seçilen güvenlik işaretleri paneli çizilir.
"""
import argparse, base64, glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
NAVY, GREEN = "#00233E", "#237F52"
DEPTS = {"uretim": ("Üretim", "Production", "#237F52"), "lojistik": ("Lojistik", "Logistics", "#FF6600"),
         "kalite": ("Kalite", "Quality", "#A43493"), "bakim": ("Bakım", "Maintenance", "#9B2423"),
         "dial": ("Dial Lab", "Dial Lab", "#005387"), "beyaz": ("Beyaz Yaka", "White collar", "#78858B")}

# (tür, emoji, TR etiket, EN etiket, anahtar kelimeler)
SIGNS = [
    ("m", "🧤", "Eldiven kullan", "Wear gloves", ["eldiven"]),
    ("m", "🥽", "Göz / yüz koruması", "Eye / face protection", ["gözlük", "yüz siperi"]),
    ("m", "🥾", "İş ayakkabısı giy", "Wear safety shoes", ["ayakkabı", "çizme"]),
    ("m", "🦺", "Reflektörlü yelek", "Hi-vis vest", ["yelek"]),
    ("m", "🔒", "Kilitle - Etiketle", "Lock out - Tag out", ["kilit", "loto", "lockout"]),
    ("w", "🧪", "Kimyasal madde", "Chemical hazard", ["kimyasal", "kostik", "asit"]),
    ("w", "🔥", "Sıcak yüzey / yangın", "Heat / fire hazard", ["sıcak", "yangın", "kaynak"]),
    ("w", "⚡", "Elektrik tehlikesi", "Electrical hazard", ["elektrik", "enerji"]),
    ("w", "🚜", "İş makinesi trafiği", "Vehicle traffic", ["forklift", "transpalet", "araç"]),
    ("w", "🔪", "Kesici alet", "Sharp tools", ["bıçak", "kesici", "kesik", "keskin"]),
    ("w", "🧲", "Güçlü manyetik alan", "Strong magnetic field", ["mıknatıs", "manyetik"]),
    ("w", "✋", "Sıkışma tehlikesi", "Crushing hazard", ["sıkış", "ezilme"]),
    ("w", "💧", "Kayma tehlikesi", "Slip hazard", ["kayma", "ıslak", "döküntü"]),
    ("m", "🧍", "Doğru duruş", "Correct posture", ["ergonomi", "duruş", "kaldır", "oturma"]),
    ("m", "⏱️", "Düzenli mola ver", "Take regular breaks", ["mola"]),
    ("m", "♻️", "Atıkları ayrıştır", "Sort the waste", ["atık"]),
    ("m", "🖥️", "Ekran başında doğru çalış", "Safe screen work", ["ekran", "bilgisayar"]),
    ("w", "🔌", "Kablo ve priz güvenliği", "Cable and socket safety", ["kablo", "priz", "uzatma"]),
    ("m", "👁️", "Göz sağlığını koru", "Protect your eyes", ["göz yorgun", "20-20-20", "kırpma"]),
    ("i", "🚿", "Göz duşu / acil duş", "Eyewash / safety shower", ["göz duşu", "acil duş"]),
    ("p", "✋", "Çalışırken müdahale etme", "Do not intervene while running", ["müdahale", "açmayın", "sokulma"]),
]
L = {"tr": {"amac": "Amaç:", "unutma": "Unutma!", "dikkat": "Bu konuda dikkat", "slogan": [("İ", "LK"), ("S", "ENİN"), ("G", "ÜVENLİĞİN!")]},
     "en": {"amac": "Purpose:", "unutma": "Remember!", "dikkat": "Watch out for", "slogan": [("Y", "OUR"), ("S", "AFETY"), ("F", "IRST!")]}}


def b64(path):
    ext = os.path.splitext(path)[1].lower().strip(".").replace("jpg", "jpeg")
    return f"data:image/{ext};base64," + base64.b64encode(open(path, "rb").read()).decode()


def sections(metin):
    secs, cur = [], None
    for raw in metin.replace("\r", "").split("\n"):
        l = raw.strip()
        if l.startswith("## "):
            cur = {"h": l[3:].strip(), "items": [], "paras": []}; secs.append(cur); continue
        if not l or cur is None: continue
        if re.match(r"^[-•]\s+", l): cur["items"].append(re.sub(r"^[-•]\s+", "", l))
        else: cur["paras"].append(l)
    return secs


def pick_signs(text, n=6):
    t = text.lower()
    scored = [(sum(t.count(k) for k in s[4]), i, s) for i, s in enumerate(SIGNS)]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [x[2] for x in scored[:n]]


def sign_svg(kind, emoji):
    if kind == "w":
        return f'<svg viewBox="0 0 100 90"><polygon points="50,4 96,86 4,86" fill="#F9A900" stroke="#1d1d1b" stroke-width="5" stroke-linejoin="round"/><text x="50" y="70" font-size="36" text-anchor="middle">{emoji}</text></svg>'
    if kind == "p":
        return '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="44" fill="#fff" stroke="#9B2423" stroke-width="10"/><text x="50" y="64" font-size="38" text-anchor="middle">✋</text><line x1="19" y1="19" x2="81" y2="81" stroke="#9B2423" stroke-width="10"/></svg>'
    fill = "#237F52" if kind == "i" else "#005387"
    return f'<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="47" fill="{fill}"/><text x="50" y="64" font-size="42" text-anchor="middle">{emoji}</text></svg>'


def build_html(w, dk, x, dil, tr_text):
    lab = L[dil]; e = html.escape
    secs = sections(x["metin"])
    amac = ""
    if secs and re.search(r"neden|why|amaç|purpose", secs[0]["h"], re.I):
        first = secs.pop(0); amac = " ".join(first["paras"] + first["items"])
    body = ""
    for i, s in enumerate(secs, 1):
        body += f'<div class="sec"><div class="sh">{i}. {e(s["h"])}</div>'
        if s["paras"]: body += "".join(f"<p>{e(p)}</p>" for p in s["paras"])
        if s["items"]: body += "<ol>" + "".join(f"<li>{e(it)}</li>" for it in s["items"]) + "</ol>"
        body += "</div>"
    foto = next((p for p in glob.glob(os.path.join(ROOT, "content", "gorsel", f"H{w}_{dk}.*")) if p.lower().endswith((".jpg", ".jpeg", ".png"))), None)
    dname = DEPTS[dk][0 if dil == "tr" else 1]; dcol = DEPTS[dk][2]
    if foto:
        visual = f'<img class="foto" src="{b64(foto)}">'
    else:
        signs = pick_signs(tr_text)
        cells = "".join(f'<div class="sg">{sign_svg(k, em)}<span>{e(trl if dil == "tr" else enl)}</span></div>' for k, em, trl, enl, _ in signs)
        visual = f'<div class="panel" style="--dc:{dcol}"><div class="ph">{e(lab["dikkat"])}</div><div class="grid n{len(signs)}">{cells}</div><div class="pf">{e(dname)}</div></div>'
    slogan = "".join(f'<b>{a}</b><span>{b}</span> ' for a, b in lab["slogan"])
    logo = b64(os.path.join(HERE, "logo.png"))
    return f"""<!DOCTYPE html><html lang="{dil}"><head><meta charset="utf-8"><style>
@page {{ size: A4 landscape; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin: 0; font-family: "DejaVu Sans", Verdana, sans-serif; color: #111; }}
.page {{ width: 297mm; height: 210mm; padding: 11mm 13mm 9mm 14mm; position: relative; display: flex; flex-direction: column }}
.top {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1.3px solid {NAVY}; padding-bottom: 3mm }}
.top h1 {{ font-size: 19pt; color: {NAVY}; margin: 0; line-height: 1.15; max-width: 205mm }}
.top .dep {{ display: inline-block; margin-top: 2mm; font-size: 8.5pt; font-weight: bold; color: #fff; background: {dcol}; border-radius: 10px; padding: 1px 9px }}
.top img {{ height: 17mm }}
.main {{ display: flex; gap: 8mm; margin-top: 3.5mm; flex: 1; min-height: 0 }}
.txt {{ flex: 1 1 0; font-size: 8.6pt; font-weight: bold; line-height: 1.33 }}
.vis {{ width: 98mm; display: flex; align-items: flex-start; justify-content: center }}
.lbl {{ font-size: 9pt }} .amac {{ margin: 0.6mm 0 2.4mm }}
.sec {{ margin-bottom: 2.2mm }} .sh {{ font-size: 9.2pt; color: {NAVY} }}
.sec p {{ margin: .6mm 0 0 6mm }}
ol {{ margin: .6mm 0 0 0; padding-left: 12mm }} li {{ margin: .25mm 0 }}
.un {{ margin-top: 1.5mm; border-left: 3.5px solid #F9A900; background: #FFF4D6; padding: 2mm 3.5mm; border-radius: 0 6px 6px 0; width: fit-content; max-width: 170mm }}
.un .h {{ font-size: 9.5pt }} .un .k {{ font-size: 10pt; margin-top: .5mm }}
.slogan {{ margin: 3mm 0 0 20mm; color: #44546A; font-size: 21pt; font-weight: normal; letter-spacing: .5px }}
.slogan b {{ font-size: 38pt }}
.foto {{ width: 98mm; max-height: 120mm; object-fit: cover; border-radius: 3mm }}
.panel {{ width: 98mm; border: 1.5px solid #d5dade; border-top: 6px solid var(--dc); border-radius: 3mm; padding: 4mm 4mm 3mm; background: #f6f8f9 }}
.ph {{ font-size: 11pt; font-weight: bold; color: {NAVY}; margin-bottom: 3mm }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4mm 3mm }}
.grid.n1 {{ grid-template-columns: 1fr }}
.sg {{ display: flex; flex-direction: column; align-items: center; gap: 1.5mm; text-align: center; font-size: 8.5pt; font-weight: bold }}
.sg svg {{ width: 24mm; height: 24mm }} .sg svg text {{ font-family: "Noto Color Emoji" }}
.pf {{ margin-top: 3mm; text-align: right; font-size: 8pt; color: #78858B; font-weight: bold }}
.foot {{ position: absolute; right: 13mm; bottom: 7mm; display: flex; align-items: center; gap: 2.5mm; color: {NAVY} }}
.foot .a {{ font-size: 12pt; font-weight: bold; line-height: 1.05; text-align: right; letter-spacing: .3px }}
.foot .b {{ border-left: 1.2px solid {NAVY}; padding-left: 2.5mm; font-size: 5.6pt; line-height: 1.45; letter-spacing: .4px }}
</style></head><body><div class="page">
<div class="top"><div><h1>{e(x["t"])}</h1><span class="dep">{e(dname)}</span></div><img src="{logo}"></div>
<div class="main"><div class="txt">
{f'<div class="lbl">{lab["amac"]}</div><div class="amac">{e(amac)}</div>' if amac else ''}
{body}
<div class="un"><div class="h">⚠️ {lab["unutma"]}</div><div class="k">“{e(x["key"])}”</div></div>
<div class="slogan">{slogan}</div>
</div><div class="vis">{visual}</div></div>
<div class="foot"><div class="a">WE BRING<br>IDEAS TO LIFE.</div><div class="b">NATURAL INGREDIENTS<br>INGREDIENT SYSTEMS<br>INTEGRATED SOLUTIONS</div></div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hafta", type=int, required=True); ap.add_argument("--dil", default="tr", choices=["tr", "en"])
    ap.add_argument("--cikti", default="cikti"); ap.add_argument("--departman")
    a = ap.parse_args()
    d = json.load(open(os.path.join(ROOT, "content", "hafta", f"H{a.hafta}.json"), encoding="utf-8"))["departmanlar"]
    os.makedirs(a.cikti, exist_ok=True)
    from playwright.sync_api import sync_playwright
    exe = next((p for p in ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"] if os.path.exists(p)), None)
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        pg = b.new_page()
        for dk in DEPTS:
            if dk not in d or (a.departman and dk != a.departman): continue
            x = d[dk].get(a.dil) or d[dk]["tr"]
            tr_text = d[dk]["tr"]["metin"] + " " + " ".join(d[dk]["tr"]["rules"])
            pg.set_content(build_html(a.hafta, dk, x, a.dil, tr_text)); pg.wait_for_timeout(300)
            fn = os.path.join(a.cikti, f"H{a.hafta}_{dk}{'_en' if a.dil == 'en' else ''}.pdf")
            pg.pdf(path=fn, format="A4", landscape=True, print_background=True, prefer_css_page_size=True)
            out.append(fn)
        b.close()
    print(json.dumps({"dosyalar": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
