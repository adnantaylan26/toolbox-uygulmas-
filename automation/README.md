# Haftalık toolbox afişleri

Her cuma 15:30'da (İstanbul) zamanlanmış görev bu aracı çalıştırır ve bir sonraki haftanın kartlarını üretir.

    python3 automation/haftalik_afis.py [--tarih YYYY-MM-DD] [--cikti klasor]

- Eğitim haftası → departman başına 1 kart (konu, 3 ana kural, "Unutmayın" mesajı, QR)
- Tekrar haftası → departman başına 5 konuluk tekrar kartı + sınav tarihi
- Sınav Pazartesisi → "Genel tekrar sınavı" kartı

Konular `automation/plan.json` içindedir. Yeni dönem için `donemler` listesine
`{ad, baslangic (ilk Pazartesi), haftalar, konular{departman{hafta{t, rules[3], key}}}}` eklenir.
Departman anahtarları: uretim, lojistik, dial, bakim, kalite.
Kişisel veri (personel listesi, yedek JSON) bu klasöre konmaz.
