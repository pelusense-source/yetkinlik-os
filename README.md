# Yetkinlik OS — Günlük otomatik bülten (kurulabilir sürüm)

Bu paket, mevcut Yetkinlik OS uygulamasının kişisel gelişim/görev/ders/kaynak özelliklerini koruyarak **günlük bülten** ekler. Kaynaklar `config/sources.json` içindedir. Uygulama `site/index.html`, bülten verisi `site/data/news.json` dosyasındadır.

## Önemli: Kendiliğinden başlamaz

Bilgisayarında yalnızca HTML dosyasını açarsan kaynaklar otomatik toplanmaz. **Bir kez GitHub üzerinden yayımlaman gerekir.** Kurulum yapılana kadar örnek makaleler görünür; bunlar yeni içerik değildir.

## İlk kurulum (GitHub Pages)

1. GitHub hesabınla `yetkinlik-os` adlı bir **yeni depo** aç (kişisel yerel kayıtlarını veya şifrelerini depoya yükleme).
2. Bu ZIP içindeki **tüm klasörleri ve dosyaları** depoya yükle. Gizli `.github/workflows/daily-news.yml` klasörünün de yüklenmiş olduğunu doğrula. Ana dal `main` olsun. (GitHub web arayüzünden zip dosyasını olduğu gibi yüklemek **yeterli değildir**; zip'i açıp dosyaları eklemen gerekir.)
3. Depoda `Settings → Pages → Build and deployment → Source → GitHub Actions` seç.
4. `Actions → Günlük bülteni topla ve uygulamayı yayımla → Run workflow` ile ilk yayını elle başlat. `Actions` sayfasında çalışmanın başarılı olduğunu kontrol et.
5. Yayın URL'n genellikle `https://KULLANICI-ADIN.github.io/yetkinlik-os/` olur. Bu adresi bilgisayarına/telefonuna yer imi olarak kaydet; uygulama kapalıyken de günlük tarama sunucuda çalışır.

**Günlük zaman:** `06:37 UTC = İstanbul saatiyle 09:37`. GitHub zamanlanmış görevleri yoğunluk durumuna göre gecikebilir, bazı tetiklemeler gerçekleşmeyebilir. Kesin teslimat saati taahhüt edilmez. Bir public depoda uzun süre etkinlik olmazsa zamanlama askıya alınabilir. Arayüzde **Son tarama** tarihine bak.

## Yeni kaynak eklemek / düzenlemek

- Uygulama `Bülten Merkezi → Takip Kaynaklarım → + Kaynak ekle` üzerinden kaynaklarını kendin ekleyebilir, düzenleyebilir ve silebilirsin. Bunlar önce tarayıcıda saklanır.
- Otomatik taramaya da eklemek için aynı sayfadaki **Otomatik tarama listemi indir** düğmesine bas. İnen `sources.json` dosyasını GitHub deponda `config/sources.json` dosyasıyla değiştirip `main` dalına commit et. Bir sonraki yayın döngüsü bunu kullanacak; push olayı da ilk taramayı başlatabilir.
- Varsa kesin RSS/Atom URL'sini gir. Yoksa önce site içindeki RSS keşfi denenir, sonra **Google News RSS site araması** kullanılır. Bu ikinci yöntem bir yayıncının tüm yazılarını yakalamayabilir.
- Daniel Kahneman tarihsel/arşiv kaynağıdır; tarama yapılmaz. Bazı eğitim platformlarında ve podcastlerde yeni içerik bulunamayabilir. Durum uygulamada gösterilir.

## Bülten kaydı ve gizlilik

- Toplama kodu, yayınlardan **başlık, URL, tarih ve RSS'te yayımlanan kısa açıklamayı** alır; tüm makaleyi kopyalamaz, AI ile otomatik Türkçeye çevirmediği gibi kişisel yorum üretmez.
- İçerikler kaynak URL'si üzerinden açılır. Okundu, kaydedildi, notlar ve kendi eklediklerin tarayıcının `localStorage` alanında kalır; cihazlar arasında otomatik eşitlenmez.
- GitHub Pages herkese açık olabileceğinden gizli notlarını bu kamuya açık yayın klasörüne ekleme. Kendi kayıtların JSON yedek dosyasında tutulabilir.
- Başlıklar ve 45 günlük özet arşivi `site/data/news.json` dosyasında yayımlanır. JSON'a erişilebilmesi, özel bilgi yayımlandığı anlamına gelmez: yalnızca herkese açık haber başlıklarıdır.
- Kullanıcı eklediği yeni kaynak için URL GitHub deposuna aktarılmadıkça otomatik takip *aktif olmaz*.

## Teknik

- Harici ücretli API veya API anahtarı gerekmez.
- `scripts/fetch_news.py`: Python standart kütüphanesiyle RSS ve Atom kaynaklarını alır, sayfadaki feed bağlantılarını keşfeder, gerektiğinde Google News RSS aramasını dener; eski kayıtları 45 gün tutar ve her kaynağın durumunu raporlar.
- `.github/workflows/daily-news.yml`: her gün veri toplar, repoya kaydeder, GitHub Pages'e yeniden yayımlar.
- `site/sw.js`: günlük veri için *network-first* davranışı uygular; eski önbellek güncelleme sinyalini engellemez.
- `python -m unittest discover -s tests -v`: internet gerektirmeyen feed ayrıştırma testleri.

Yayın araçları düzenlenebileceği için GitHub'ın dokümantasyonuna bakabilirsin:
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows


## Günün Özeti — günlük 3–5 dakikalık brifing

Bülten Merkezi içindeki **Günün Özeti** sekmesi, her günlük haber taramasından sonra otomatik hazırlanır. Önemli başlıklar alanlara ayrılır, 10 adede kadar içerik seçilir ve her birinin altında **Asıl makaleyi oku** bağlantısı görünür. Günün Özeti sekmesindeki içerikler `site/data/news.json` içinde `dailyDigest` ve son 14 kayıtlık `digestHistory` alanlarında saklanır.

**İki çalışma modu:**

- **API anahtarı olmadan (başlık temelli):** Başlıklar ve RSS yayıncı açıklamaları derlenir. Tam makalenin özetlendiği iddia edilmez. Kaynağın açıklaması İngilizceyse özgün dilinde kalabilir.
- **AI ile Türkçe özetleme:** GitHub deposu → **Settings → Secrets and variables → Actions → New repository secret** yolunu aç. Secret adı `OPENAI_API_KEY`, değeri kendi OpenAI API anahtarın olsun. Anahtarı sohbet içinde paylaşma, koda veya Public depoya ekleme. Opsiyonel olarak **Variables → New repository variable** ile `OPENAI_MODEL` model adını belirleyebilirsin; varsayılan `gpt-4.1-mini`. `Actions → Günlük bülteni topla ve uygulamayı yayımla → Run workflow` komutunu çalıştır.

Anahtar tanımlandığında API tüketim ücreti, ChatGPT aboneliğinden ayrı olarak OpenAI API hesabına yansıyabilir. Tarama günlük yaklaşık 10 seçilmiş başlık ve varsa RSS yayıncı açıklamasını özetletir. Model, tam makaleleri taramaz; sadece mevcut RSS verisini yorumlar. Kaynak açıklaması yetersizse sınırlılığı belirtir. API başarısız olursa açıkça işaretli başlık temelli bültene dönülür. Ücret ve kullanım sınırlarını API hesabından kontrol et.

İlk çalıştırmanın ardından tarayıcıdan GitHub Pages adresini yenile. Eski görünüm görünüyorsa önbellek için tam yenile (Ctrl+F5) kullan.