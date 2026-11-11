#!/usr/bin/env python3
"""Yıllık toolbox planı Excel'ini (Yıllık Plan sayfası) content/yillik_plan.json dosyasına çevirir.

    python3 automation/yillik_plan_yukle.py plan.xlsx
Sütunlar: Hafta | Pazartesi | Tür | Üretim | Lojistik | Kalite | Teknik Bakım | Dial Lab | Beyaz Yaka
"""
import json, os, sys
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLS = {"üretim": "uretim", "lojistik": "lojistik", "kalite": "kalite", "teknik bakım": "bakim", "bakım": "bakim", "dial lab": "dial", "dial": "dial", "beyaz yaka": "beyaz"}


def main(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Yıllık Plan"] if "Yıllık Plan" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr_i = next(i for i, r in enumerate(rows) if r and any(str(c or "").strip().lower() == "hafta" for c in r))
    hdr = [str(c or "").strip().lower() for c in rows[hdr_i]]
    wcol = hdr.index("hafta"); dcols = {i: COLS[h] for i, h in enumerate(hdr) if h in COLS}
    plan = {}
    for r in rows[hdr_i + 1:]:
        if not r or r[wcol] in (None, ""): continue
        try: w = int(str(r[wcol]).upper().replace("H", "").strip())
        except ValueError: continue
        for i, dk in dcols.items():
            t = str(r[i] or "").strip()
            if t and "TEKRAR HAFTASI" not in t.upper(): plan.setdefault(str(w), {})[dk] = t
    out = os.path.join(ROOT, "content", "yillik_plan.json")
    old = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    old.update(plan)
    json.dump(dict(sorted(old.items(), key=lambda x: int(x[0]))), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"dosya": out, "hafta_sayisi": len(plan), "haftalar": sorted(int(k) for k in plan)}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
