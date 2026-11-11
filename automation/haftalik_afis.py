#!/usr/bin/env python3
"""Haftalık toolbox duyuru kartları.

Kullanım:  python3 automation/haftalik_afis.py [--tarih YYYY-MM-DD] [--cikti klasor]

--tarih verilmezse bugün (İstanbul) alınır. Betik, bu tarihten sonraki ilk
Pazartesi gününe denk gelen haftayı plan.json'da arar ve şunları üretir:
  * dönem haftasıysa: her departman için 1 kart (konu, 3 ana kural, unutmayın)
  * tekrar haftasıysa: departman başına tekrar haftası kartı
  * genel sınav Pazartesi'siyse: 1 sınav duyuru kartı
Sonuç özetini JSON olarak stdout'a yazar.
"""
import argparse, json, os, sys, datetime as dt
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
APP_URL = "https://dohler-toolbox.netlify.app"
# Döhler Görsel Uygulama Rehberi renkleri
NAVY = (0, 35, 62); BLUE = (0, 83, 135); GREEN = (35, 127, 82); YELLOW = (249, 169, 0)
RED = (155, 36, 35); ORANGE = (255, 102, 0); GREY = (120, 133, 139); WHITE = (255, 255, 255)
INK = (21, 32, 43); SOFT = (238, 241, 244)
DEPTS = {
    "uretim":   {"ad": "Üretim",       "renk": GREEN},
    "lojistik": {"ad": "Lojistik",     "renk": ORANGE},
    "dial":     {"ad": "Dial Lab",     "renk": BLUE},
    "bakim":    {"ad": "Bakım",        "renk": RED},
    "kalite":   {"ad": "Kalite",       "renk": (164, 52, 147)},
}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
W, H = 1080, 1350


def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for root in ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts"]:
        for n in names:
            p = os.path.join(root, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    for dirpath, _, files in os.walk("/usr/share/fonts"):
        for n in names:
            if n in files:
                return ImageFont.truetype(os.path.join(dirpath, n), size)
    return ImageFont.load_default()


def tr_tarih(d):
    return f"{d.day} {AYLAR[d.month - 1]}"


def wrap(draw, text, fnt, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def qr_image(url, box=8):
    from reportlab.graphics.barcode.qrencoder import QRCode, QRErrorCorrectLevel
    q = QRCode(4, QRErrorCorrectLevel.M); q.addData(url); q.make()
    n = q.getModuleCount(); pad = 2
    img = Image.new("RGB", ((n + pad * 2) * box,) * 2, WHITE); d = ImageDraw.Draw(img)
    for r in range(n):
        for c in range(n):
            if q.isDark(r, c):
                x, y = (c + pad) * box, (r + pad) * box
                d.rectangle([x, y, x + box - 1, y + box - 1], fill=(0, 0, 0))
    return img


def icon(draw, cx, cy, r, color):
    """İSG uyarı üçgeni ikonu."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    t = r * 0.62
    pts = [(cx, cy - t), (cx + t * 0.95, cy + t * 0.65), (cx - t * 0.95, cy + t * 0.65)]
    draw.polygon(pts, fill=YELLOW)
    f = font(int(r * 0.7), True)
    draw.text((cx, cy + t * 0.12), "!", font=f, fill=NAVY, anchor="mm")


def header(img, draw, chip_text, chip_color):
    draw.rectangle([0, 0, W, 190], fill=NAVY)
    draw.rectangle([0, 190, W, 200], fill=GREEN)
    logo_p = os.path.join(HERE, "logo.png")
    if os.path.exists(logo_p):
        lg = Image.open(logo_p).convert("RGB"); h = 100; lg = lg.resize((int(lg.width * h / lg.height), h))
        draw.rounded_rectangle([50, 45, 50 + lg.width + 30, 45 + h + 20], 16, fill=WHITE)
        img.paste(lg, (65, 55))
    f = font(34, True)
    tw = draw.textlength(chip_text, font=f)
    draw.rounded_rectangle([W - 60 - tw - 50, 72, W - 60, 128], 28, fill=chip_color)
    draw.text((W - 60 - tw / 2 - 25, 100), chip_text, font=f, fill=WHITE, anchor="mm")


def footer(img, draw, line, l1="Eğitimi okuyup 5 soruluk", l2="quizi uygulamadan çözün"):
    draw.rectangle([0, H - 230, W, H], fill=SOFT)
    q = qr_image(APP_URL, 6).resize((170, 170), Image.NEAREST)
    img.paste(q, (60, H - 200))
    draw.text((260, H - 170), l1, font=font(32), fill=INK)
    draw.text((260, H - 128), l2, font=font(32), fill=INK)
    draw.text((260, H - 78), line, font=font(26, True), fill=NAVY)


def week_card(dept, info, week, monday, out):
    d = DEPTS[dept]; img = Image.new("RGB", (W, H), WHITE); draw = ImageDraw.Draw(img)
    header(img, draw, d["ad"], d["renk"])
    icon(draw, 120, 300, 60, d["renk"])
    draw.text((205, 268), f"HAFTA {week}", font=font(30, True), fill=GREY)
    draw.text((205, 306), f"{tr_tarih(monday)} – {tr_tarih(monday + dt.timedelta(days=4))}", font=font(30), fill=GREY)
    y = 400; ft = font(54, True)
    for ln in wrap(draw, info["t"], ft, W - 120)[:4]:
        draw.text((60, y), ln, font=ft, fill=NAVY); y += 66
    y += 24
    draw.text((60, y), "Ana kurallar", font=font(34, True), fill=d["renk"]); y += 56
    fr = font(32)
    for rule in info.get("rules", [])[:3]:
        draw.ellipse([62, y + 6, 92, y + 36], fill=d["renk"])
        draw.text((77, y + 21), "✓", font=font(22, True), fill=WHITE, anchor="mm")
        lines = wrap(draw, rule, fr, W - 230)[:3]
        for ln in lines:
            draw.text((112, y), ln, font=fr, fill=INK); y += 42
        y += 18
    if info.get("key"):
        fk = font(32, True); lines = wrap(draw, info["key"], fk, W - 200)[:3]
        bh = 40 + 44 * len(lines) + 40
        y = max(y + 10, H - 250 - bh - 20)
        draw.rounded_rectangle([50, y, W - 50, y + bh], 18, fill=(255, 244, 214))
        draw.rectangle([50, y, 62, y + bh], fill=YELLOW)
        draw.text((90, y + 22), "UNUTMAYIN", font=font(24, True), fill=(133, 79, 11))
        yy = y + 58
        for ln in lines:
            draw.text((90, yy), ln, font=fk, fill=INK); yy += 44
    footer(img, draw, APP_URL.replace("https://", ""))
    img.save(out, optimize=True)


def review_card(dept, items, week, monday, exam, out):
    d = DEPTS[dept]; img = Image.new("RGB", (W, H), WHITE); draw = ImageDraw.Draw(img)
    header(img, draw, d["ad"], d["renk"])
    icon(draw, 120, 300, 60, YELLOW)
    draw.text((205, 268), f"HAFTA {week} · TEKRAR HAFTASI", font=font(30, True), fill=GREY)
    draw.text((205, 306), f"{tr_tarih(monday)} – {tr_tarih(monday + dt.timedelta(days=4))}", font=font(30), fill=GREY)
    y = 400
    draw.text((60, y), "5 haftanın konularını", font=font(52, True), fill=NAVY); y += 64
    draw.text((60, y), "tekrar edin", font=font(52, True), fill=NAVY); y += 90
    fr = font(30)
    for i, (w, t) in enumerate(items[:5]):
        draw.text((60, y), f"H{w}", font=font(30, True), fill=d["renk"])
        for ln in wrap(draw, t, fr, W - 220)[:2]:
            draw.text((160, y), ln, font=fr, fill=INK); y += 40
        y += 16
    if exam:
        y = max(y + 10, H - 400)
        draw.rounded_rectangle([50, y, W - 50, y + 120], 18, fill=(255, 244, 214))
        draw.rectangle([50, y, 62, y + 120], fill=YELLOW)
        draw.text((90, y + 22), "GENEL TEKRAR SINAVI", font=font(24, True), fill=(133, 79, 11))
        draw.text((90, y + 60), f"{tr_tarih(exam)} Pazartesi", font=font(36, True), fill=INK)
    footer(img, draw, APP_URL.replace("https://", ""), "Tekrar için eğitimleri", "uygulamadan yeniden okuyun")
    img.save(out, optimize=True)


def exam_card(monday, title, out):
    img = Image.new("RGB", (W, H), WHITE); draw = ImageDraw.Draw(img)
    header(img, draw, "Tüm departmanlar", NAVY)
    icon(draw, W // 2, 420, 110, NAVY)
    y = 590
    for ln, f, c in [("Genel tekrar sınavı", font(64, True), NAVY), (f"{tr_tarih(monday)} Pazartesi", font(48, True), GREEN), (title, font(32), GREY)]:
        draw.text((W // 2, y), ln, font=f, fill=c, anchor="mm"); y += 90
    y += 10
    for ln in ["17 soru · Geçme notu 70", "Sınav o hafta boyunca açık kalır", "Yalnızca bir kez girilebilir"]:
        draw.text((W // 2, y), ln, font=font(34), fill=INK, anchor="mm"); y += 56
    footer(img, draw, APP_URL.replace("https://", ""), "Sınava Sicil No ile", "uygulamadan girin")
    img.save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarih"); ap.add_argument("--cikti", default="cikti")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.tarih) if a.tarih else dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()
    monday = today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
    plan = json.load(open(os.path.join(HERE, "plan.json"), encoding="utf-8"))
    os.makedirs(a.cikti, exist_ok=True)
    result = {"pazartesi": monday.isoformat(), "kartlar": [], "notlar": []}
    for cyc in plan.get("donemler", []):
        start = dt.date.fromisoformat(cyc["baslangic"]); weeks = cyc["haftalar"]; n = len(weeks)
        exam = start + dt.timedelta(days=7 * (n + 1))
        idx = (monday - start).days // 7
        if 0 <= idx < n:
            w = weeks[idx]
            for dk in DEPTS:
                info = cyc.get("konular", {}).get(dk, {}).get(str(w))
                if not info:
                    result["notlar"].append(f"{DEPTS[dk]['ad']} için H{w} konusu planda yok"); continue
                out = os.path.join(a.cikti, f"H{w}_{dk}.png"); week_card(dk, info, w, monday, out)
                result["kartlar"].append({"dosya": out, "tur": "hafta", "hafta": w, "departman": DEPTS[dk]["ad"], "konu": info["t"]})
        elif idx == n:
            for dk in DEPTS:
                items = [(w, (cyc.get("konular", {}).get(dk, {}).get(str(w)) or {}).get("t", "")) for w in weeks]
                if not any(t for _, t in items): continue
                out = os.path.join(a.cikti, f"H{weeks[-1] + 1}_tekrar_{dk}.png"); review_card(dk, items, weeks[-1] + 1, monday, exam, out)
                result["kartlar"].append({"dosya": out, "tur": "tekrar", "hafta": weeks[-1] + 1, "departman": DEPTS[dk]["ad"]})
        if monday == exam:
            out = os.path.join(a.cikti, f"genel_sinav_{monday.isoformat()}.png"); exam_card(monday, cyc.get("ad", ""), out)
            result["kartlar"].append({"dosya": out, "tur": "sinav", "donem": cyc.get("ad", "")})
    if not result["kartlar"]:
        result["notlar"].append(f"{tr_tarih(monday)} haftası için planda yeni dönem konusu yok; yeni dönemin konu listesi yüklenmeli")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
