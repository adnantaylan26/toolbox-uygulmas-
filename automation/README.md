# Haftalık toolbox afişleri

Her cuma 15:30'da (İstanbul) zamanlanmış görev bu aracı çalıştırır ve bir sonraki haftanın kartlarını üretir.

    python3 automation/haftalik_afis.py [--tarih YYYY-MM-DD] [--cikti klasor]

- Eğitim haftası → departman başına 1 kart (konu, 3 ana kural, "Unutmayın" mesajı, QR)
- Tekrar haftası → departman başına 5 konuluk tekrar kartı + sınav tarihi
- Sınav Pazartesisi → "Genel tekrar sınavı" kartı

Konular `automation/plan.json` içindedir. Döngü haftalıktır: 5 eğitim haftası + 1 tekrar haftası; tekrar haftasından sonraki Pazartesi genel sınav yapılır ve aynı gün yeni eğitim haftası başlar (H33–37 eğitim, H38 tekrar, H39 sınav + eğitim, ... H44 tekrar, H45 sınav + eğitim).
Yeni konu: `konular[departman][hafta_no] = {t, rules[3], key}`. Departman anahtarları: uretim, lojistik, dial, bakim, kalite.
Kişisel veri (personel listesi, yedek JSON) bu klasöre konmaz.

## Eğitim föyü (A4 yatay PDF)

    python3 automation/egitim_pdf.py --hafta 39 [--dil en] [--departman uretim] --cikti klasor

Döhler föy formatı: başlık + logo, Amaç, numaralı bölümler, "Unutma!" kutusu, "İLK SENİN GÜVENLİĞİN!" sloganı,
sağda görsel. Görsel için `content/gorsel/H39_uretim.jpg` gibi bir fotoğraf konursa o kullanılır; yoksa konuya
göre güvenlik işaretleri paneli çizilir. Playwright + Chrome/Chromium gerekir.
