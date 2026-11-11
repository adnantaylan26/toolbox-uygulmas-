# İSG Toolbox Eğitimi — Netlify kurulumu

Çalışanlar QR kodu okutup **sicil numarasıyla** giriş yapar; hesap gerekmez.
Yönetim ekranları (Takip, Konular, Eğitim geçmişi, Rapor, Personel) yalnızca **yönetici şifresiyle** açılır.

## Klasör yapısı

```
public/index.html          Uygulama arayüzü
public/backend.js          Arayüzü Netlify API'sine bağlayan köprü
netlify/functions/api.mjs  Sunucu: yönetici girişi, veri, yapay zeka, çalışan sınavları
netlify/functions/lib/logic.mjs  Soru seçme, puanlama, takvim kuralları
netlify.toml, package.json
```

Veriler **Netlify Blobs**'ta saklanır (ek veritabanı gerekmez). Sınav soruları ve doğru cevaplar
sunucuda kalır; çalışanın telefonuna cevap anahtarı gönderilmez, puanlama sunucuda yapılır.

## Kurulum (yaklaşık 15 dakika)

1. **Verilerinizi Claude'dan alın.** Claude'daki uygulamada *Personel → Yedek → Yedek indir (JSON)*.
   Bu dosyada dönemler, sorular, eğitim metinleri, personel listesi, eğitim geçmişi ve sonuçlar var.
   Kişisel veri içerdiği için GitHub'a **yüklemeyin**.
2. **GitHub'a yükleyin.** Bu klasörün içeriğini yeni (tercihen *private*) bir GitHub deposuna yükleyin.
3. **Netlify'da site oluşturun.** app.netlify.com → *Add new site → Import an existing project* →
   GitHub deposunu seçin. Ayarlar `netlify.toml`'dan otomatik gelir; *Deploy*'a basın.
4. **Ortam değişkenlerini girin.** *Site configuration → Environment variables*:

   | Değişken | Değer |
   |---|---|
   | `ADMIN_PASSWORD` | Yönetici şifresi (en az 12 karakter) |
   | `SESSION_SECRET` | Uzun rastgele bir metin (ör. 40 karakter) |
   | `ANTHROPIC_API_KEY` | console.anthropic.com'dan alınan API anahtarı (klasik soruların değerlendirmesi ve yapay zeka yorumları için) |
   | `ANTHROPIC_MODEL` | İsteğe bağlı. Varsayılan `claude-haiku-5-5` (hızlı ve ucuz) |

   Değişkenleri girdikten sonra *Deploys → Trigger deploy* ile yeniden yayınlayın.
5. **Verileri yükleyin.** Siteyi açın → en alttaki *Yönetici girişi* → *Personel → Yedekten yükle*
   → 1. adımdaki JSON dosyasını seçin.
6. **Paylaşın.** *Personel → Paylaşım · QR kod* bölümünden A4 afişi indirin. QR artık Netlify adresinizi açar.

İsterseniz *Domain management*'tan `toolbox.sirketiniz.com` gibi özel bir alan adı bağlayabilirsiniz.

## Günlük kullanım

- **Çalışan:** QR → sicil no → haftalık eğitimi oku → 5 soruluk quiz. Tekrar haftasında 5 konunun özeti
  ve tekrar quizi; ardından Pazartesi genel tekrar sınavı (otomatik açılır, o hafta açık kalır).
- **Yönetici:** *Takip* (eksikler, departman oranları), *Eğitim geçmişi* (Excel'den gelen eğitimler,
  eksik eğitimler, yasal süre), *Konular* (yeni dönem, sorular, genel sınav ayarı), *Rapor* (CSV).
- Yeni eğitim Excel'i: *Eğitim geçmişi → Eğitim Excel'i yükle*. Personel değişikliği: *Personel → Excel yükle*.

## Bilmeniz gerekenler

- **Kimlik doğrulama sicil numarasıyladır.** Başkasının sicilini bilen biri onun yerine sınava girebilir;
  bu, kâğıt sınavdaki ve kiosk düzenindeki riskle aynıdır. Daha sıkı kontrol gerekirse (ör. doğum yılı
  ile ikinci doğrulama) eklenebilir.
- **Yapay zeka maliyeti:** Her genel sınavda en fazla 1 kısa değerlendirme çağrısı yapılır (Haiku ile
  kişi başı birkaç kuruş). Anahtar tanımlı değilse klasik sorular "Kontrol bekliyor" olarak yöneticiye düşer.
- **Süre sınırı:** Netlify fonksiyonları ücretsiz planda 10 saniyede kesilir. Varsayılan Haiku modeli bu
  süreye sığar; daha büyük bir model seçerseniz zaman aşımı olabilir.
- **KVKK:** Personel adı, sicil ve eğitim kayıtları Netlify Blobs'ta (Netlify'ın bulut altyapısı) tutulur.
  Kurum içi onay ve aydınlatma metninizi buna göre güncelleyin. Yönetici olmayan ziyaretçiler hiçbir
  personel listesine veya sonuca erişemez; yalnızca kendi sicilleriyle kendi durumlarını görürler.
- **Yedek:** *Personel → Yedek indir* ile düzenli yedek alın.

## Haftalık içerik otomasyonu (Kasım 2026)

- `content/hafta/H{n}.json`: haftanın 5 departman içeriği (TR + EN): metin, 3 kural, unutmayın, 5 D/Y, 3 ÇS, 1 klasik.
- `content/yillik_plan.json`: yıllık Excel planından gelen başlıklar (`automation/yillik_plan_yukle.py plan.xlsx`).
- `automation/icerik_derle.py` → `netlify/functions/lib/content.mjs`. Sunucu ilk istekte 5 haftalık dönemi
  (`auto_H39`, `auto_H45`, …) kendisi oluşturur/günceller; ayrıca yedek yüklemeye gerek yok.
- Döngü: 5 eğitim + 1 tekrar haftası; tekrar sonrası Pazartesi önceki dönemin genel sınavı açılır ve yeni dönem başlar.
  Çalışan o hafta hem yeni haftanın eğitimini hem önceki dönemin sınavını görür.
- Dil: çalışan ekranında TR/EN düğmesi; `?lang=en` bağlantısı İngilizce açar. Kartlar: `haftalik_afis.py --dil en`.
