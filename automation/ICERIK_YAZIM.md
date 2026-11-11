# Haftalık içerik yazım kuralları (content/hafta/H{hafta}.json)

Kaynak başlıklar: `content/yillik_plan.json` (Excel'den) veya kullanıcının sohbette yazdığı konular.
Örnek ve tam biçim: `content/hafta/H39.json`.

Her departman (`uretim`, `lojistik`, `kalite`, `bakim`, `dial`) için `tr` ve `en` blokları:

- `t`: konu başlığı (kullanıcının başlığı; yazım hatası varsa düzelt, anlamını değiştirme)
- `metin`: 180–300 kelime, sade dil, Döhler meyve suyu/gıda fabrikası bağlamı. `## Başlık` ve `- madde` biçimi.
  Önerilen bölümler: Neden önemli? · Başlamadan önce / Doğru uygulama · Yapılmaması gerekenler · Acil durumda
  (Ana kurallar ve Unutmayın bölümlerini metne YAZMA; derleyici `rules` ve `key` alanından ekler.)
- `rules`: tam 3 kısa ana kural (kartta görünür, her biri en fazla ~90 karakter)
- `key`: tek cümlelik akılda kalıcı "Unutmayın" mesajı (≤ 100 karakter)
- `tf`: 5 Doğru/Yanlış ifade (`a`: true/false), en az 2 tanesi yanlış
- `mc`: 3 çoktan seçmeli soru, 4 şık, `a` = doğru şıkkın 0'dan başlayan sırası; doğru şıkkı farklı konumlara dağıt
- `classic`: 1 açık uçlu soru + `key` (beklenen cevap, puanlamada kullanılır; "herhangi ikisi yeterli" gibi esneklik belirt)

`en` bloğu `tr`'nin birebir çevirisi olmalı; soru sayıları ve doğru cevap sıraları aynı kalmalı.
Bilgiler doğru ve güncel İSG uygulamasına uygun olmalı; tıbbi/teknik iddiada abartı yapma.

Yazdıktan sonra: `python3 automation/icerik_derle.py` (hata vermemeli) → commit + push.
Netlify yayına aldığında uygulama içeriği kendisi yükler (yeni 5 haftalık dönem otomatik açılır).
