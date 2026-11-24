# Doruk — Week 3 çalışma rehberi

Senin sunum bölümün **7–12. slaytlar**, yaklaşık **2 dakika 20 saniye**. Konun: kaynağı nasıl bulduğumuz, bunu nasıl ölçtüğümüz ve hatanın hangi aşamada oluştuğunu nasıl ayırdığımız.

## Projenin bu haftaki işi

Beldesk, kurgusal Yeşilvadi Belediyesi için Türkçe ve İngilizce çalışan bir yardımcı. Week 3’te vatandaşın sorusuyla ilgili belgeleri buluyor, bunları cevap modeline veriyor ve cevabın kaynaklarını numaralandırıyoruz. Bu yaklaşım **RAG** olarak adlandırılıyor.

Akış şöyle:

**Belgeler → parçalar → BM25 ve anlamsal arama → RRF → reranker → yetkili kaynaklar → kaynaklı cevap → iddia değerlendirmesi.**

Henüz gerçek belediye veritabanına bağlanmıyoruz; kayıt açma, ödeme veya ekip gönderme aracı yok. Kaynaklarımız da gerçek belediye mevzuatı değil, açıkça belirtilmiş sentetik proje belgeleri.

## 7. slayt — Kaynak bulma sonuçları

32 cevaplanabilir sorunun **31’inde** doğru kaynak ilk beş sonuçta bulunuyor. **Hit@5 = 31/32 = 0.96875.** Bu, yaklaşık %97 kaynak bulma başarısıdır; %97 doğru cevap anlamına gelmez.

- **Hit@1:** Doğru kaynak ilk sırada mı? Sonuç 30/32.
- **Hit@3, @5, @10:** Doğru kaynak belirtilen ilk kaç sonuç arasında? Üçünde de 31/32.
- **MRR@10 = 0.953125:** Doğru kaynağın ne kadar erken geldiğini ölçer. İlk sıradaysa 1, ikinciyse 1/2, üçüncüyse 1/3 puan verir; ilk 10’da yoksa 0. Bu puanların ortalaması alınır.

Ölçüm, yalnız belge kimliğinin eşleşmesini değil, beklenen paragraf ve kanıt alıntısının bulunan parçada yer almasını kontrol eder. Altı bilgi-yokluğu kontrolü, hit@k paydasına katılmaz.

**Sınır:** Küçük ve sentetik bir test. Altın etiketler taslak; sonuç bütün gerçek vatandaş sorularına genellenemez. 31/32 için %95 Wilson aralığı yaklaşık 0.843–0.994; tek bir yüzdeye fazla kesinlik yüklemiyoruz.

## 8. slayt — Ablation deneyleri

Ablation, bir bileşenin katkısını görmek için **tek şeyi değiştirerek** karşılaştırma yapmaktır.

| Düzenek | Hit@1 | Hit@5 | MRR@10 |
|---|---:|---:|---:|
| Hybrid + reranker | 30/32 | 31/32 | 0.9531 |
| Dense + reranker | 30/32 | 31/32 | 0.9531 |
| Hybrid, reranker kapalı | 23/32 | 30/32 | 0.8047 |

İlk karşılaştırmada yalnız aday bulma yöntemi değişti; reranker aynı kaldı. Hybrid, bu testte dense’den daha iyi çıkmadı. İkincide hybrid aynı kaldı, yalnız reranker kapatıldı. Doğru kaynakların erken sıralara gelmesi zayıfladı. Dolayısıyla bu küçük deney reranker’ın katkısını destekliyor; her projede aynı sonucu vereceğini söylemiyoruz.

## 9. slayt — Scoreboard

Geçen haftaki **13 metrik satırı** korunuyor. `null`, ölçümün bulunmadığı anlamına gelir; sıfır demek değildir.

Week 2’deki cevap puanı ile Week 3’teki hit@5 farklı işler ölçüyor. Test kümeleri ve yetenekler değiştiği için bunları doğrudan “başarı arttı” diye karşılaştıramayız. Yerel kaynak arama süresi ile Gemini’den cevap alma süresini de ayırıyoruz. Gerçek fatura kanıtımız olmadığı için harcamayı sıfırmış gibi yazmıyoruz.

İlk çalıştırmada 38 vakanın yalnız 2’sinden geçerli model yanıtı alınmıştı. Diğerlerinin çoğunda HTTP 503 oluştu. Bu, 36 yanlış cevap demek değildir: çoğunda cevap hiç oluşmadı. Yeniden deneme aynı modeli, soruları ve promptu korur; yalnız servis hatalarındaki bekleme/tekrar politikasını iyileştirir. **Güncel sayıyı sunumdaki sonuçtan oku.**

Eski başarılı cevaplar önbellekten kullanılmışsa ayrıca belirtilir. Bu nedenle yeniden denemeyi 38 bağımsız yeni üretim veya kanıtlanmış kalite artışı olarak anlatma.

## 10. slayt — Faithfulness

Faithfulness, cevaptaki iddiaların verilen kaynaklara sadakatidir. Cevabı tek bir bütün olarak değil, **iddia iddia** kontrol ediyoruz.

Bir kaynak numarasının var olması veya alıntının metinde bulunması tek başına yeterli değil. Kaynak “ücret bilgisi belirtilmemiştir” derken cevap “ücretsizdir” diyorsa iddia desteklenmiyor. Teknik doğrulama alıntının varlığını kontrol eder; anlam desteğini ayrıca değerlendirmek gerekir.

Üç etiket var:

- **supported:** Kaynak iddianın bütün önemli kısımlarını destekliyor.
- **unsupported:** Kaynakla çelişki, anlamı değiştirme veya araç sonucu olmadan yapılmış işlem iddiası var.
- **insufficient_evidence:** Kaynak iddiayı doğrulayacak bilgiyi vermiyor. “Kaynakta yok” demek, gerçek hayatta tersinin doğru olduğu anlamına gelmez.

Son iki etiket toplam desteklenmeyen iddia oranında birlikte sayılır; nedenleri ayrı tutulur. Geçerli judge kararı yoksa oran `null` kalır. Az sayıda iddia değerlendirildiyse o küçük payda açıkça söylenir.

## 11. slayt — Gerçek kaynak bulma hatası

İngilizce bir soru, genel belediye hizmeti sorusu sormak için kimlik bilgisi veya belge yüklemek gerekip gerekmediğini soruyor. Beklenen gizlilik paragrafı, yeniden sıralanacak 20 adayın arasına girmedi. Daha genel hizmet paragrafları onun önüne geçti.

**Reranker kendisine hiç verilmeyen kaynağı geri getiremez.** Bu nedenle bu, öncelikle bir retrieval hatası. Modelin yanlış bir cevap ürettiğini henüz göstermiyor. Bu vakayı sonuçlardan silmiyoruz veya altın etiketi modelin bulduğuna göre değiştirmiyoruz. İyileştirmeleri ayrı geliştirme sorularında denemek gerekir.

## 12. slayt — Hatanın yerini ayırmak

| Durum | Aşama |
|---|---|
| Doğru kaynak bulunamadı | Retrieval |
| Kaynak var ama cevap onun desteklemediği bir şey söylüyor | Generation |
| Gemini HTTP 503 verdi, cevap alınamadı | Sağlayıcı / erişilebilirlik |
| Judge çalışmadı veya geçersiz çıktı üretti | Evaluation |

Bu ayrım sayesinde hangi parçayı düzelteceğimizi biliyoruz. Servis hatasını halüsinasyon oranına karıştırmıyoruz.

## Bilmen gereken teknik kelimeler

- **Corpus:** 31 belge; 30 halka açık rehber, 1 personel erişimi testi. Gövdeler Türkçe, İngilizce başlık/anahtar sözcükler de var. Soru kümesi 19 Türkçe ve 19 İngilizce: 32 cevaplanabilir soru + 6 kontrol.
- **Chunk:** Belgenin bir parçası. Bölüm yapısına göre 92 parça oluştu. 140 kelime sınırı ve uzun parçalarda 20 kelimelik örtüşme kuralı var; mevcut bölümler kısa olduğu için fiilî örtüşme sıfır.
- **BM25:** Kelime eşleşmesine dayalı arama.
- **Dense / embedding:** Metnin anlamını temsil eden sayısal vektörlerle arama. E5 modeli yerelde çalışıyor.
- **RRF:** Kelime ve anlam aramasının sıralamalarını birleştirme. İki farklı ham puanı doğrudan toplamak yerine sıra konumlarını kullanıyor.
- **Reranker:** Soru ile her aday parçayı birlikte okuyup yeniden puanlayan yerel model.
- **Access filter:** Vatandaşa kapalı personel belgeleri sıralama öncesinde çıkarılıyor. Mesaja “yöneticiyim” yazmak yetki sağlamıyor. Gerçek uygulamada rol güvenilir oturumdan gelmeli.
- **Cohen’s κ:** İnsan ile judge arasındaki uyum. Yalnız eşleşen gerçek insan–judge kararlarıyla hesaplanır; örnek sayısı yanında yazılmalı. Tek başına bir κ değeri judge’ın doğru olduğunu kanıtlamaz.

## Değerlendirme ekranındaki ilerlemen

Senin girdiğin **13 etiket korunuyor**. Kalan 7 madde ve önceki seçimlerine ilişkin açıklamalar **“Tamamlayıcı inceleme”** bölümünde. Bu ayrı öneriler insan etiketi gibi sayılmıyor. Öneriyi gördükten sonra yapılan yeni inceleme de kör değerlendirme diye sunulmamalı.

20, planladığımız inceleme sayısıydı; Week 3 yönergesi bu başlıkta 20 şartı koymuyor. Önemli olan judge’ı gerçek insan etiketleriyle karşılaştırmak ve kullanılan eşleşme sayısını açıkça belirtmek. İki gerçek müşteri görüşmesi ise hâlâ ayrı bir teslim gereği; henüz yapılmadı.

## Gelebilecek kısa sorular

**“Why not use dense only?”** Bu testte kalite farkı görmedik. Hybrid dersin istenen bileşeni; kelime eşleşmesi sağlayan ek bir yol. Daha iyi olduğunu iddia etmiyoruz.

**“Does 31/32 mean 97% correct answers?”** Hayır. Bu, doğru kaynağı bulma başarısı. Cevap doğruluğu ve kaynağa sadakat ayrı ölçümler.

**“Why is a metric null?”** Gerekli geçerli ölçüm veya payda yok. Eksik ölçümü sıfır hata veya tam başarı olarak yazmıyoruz.

**“Did you change the model?”** Hayır. Cevap modeli Gemini 3.1 Flash-Lite kaldı; embedding ve reranker yerelde çalışıyor.

**“Can Beldesk open a ticket?”** Bu Week 3 sürümünde hayır. Gerçek işlem araçları bağlı değil; belge arama ve kaynaklı cevap aşamasındayız.


## Güncel deney sonucu — 24 Kasım 2026

- İlk denemede 2/38 geçerli yanıt vardı. Aynı Gemini 3.1 Flash-Lite modeliyle, sınırlı tekrarlar ve başarılı aşamaları koruyan önbellek sayesinde **38 farklı vakanın tamamı için geçerli kayıt** elde edildi: **32 kaynaklı cevap + 6 sabit bilgi-yokluğu yanıtı**.
- Bu 38 kaydın 2’si ilk çalıştırmadan, 36’sı sonraki toparlama denemelerinden geliyor. Son tamamlama turu kendi içinde 36 kayıtlı başarıyı kullandı ve 2 yeni cevap aldı. Bunları “38 bağımsız yeni üretim” diye anlatmıyoruz.
- Kaynak judge’ı **61 iddiada 0 desteklenmeyen/yetersiz iddia** işaretledi. Bu, “kesinlikle hiç hata yok” kanıtı değil; sınırlı insan karşılaştırmasına dayanan geçici bir model ölçümü.
- Tarihsel inceleme kümesindeki **13 gerçek insan–judge çifti** için **8 karar aynı, 5 karar farklı**. Cohen’s κ yaklaşık **0.387**. Kaynakta olmayan bilgiyle çelişen bilgi arasındaki ayrım ve insan etiketlerinin ikinci kez kontrol edilmemiş olması önemli. Judge’ın doğruluğu kanıtlandı demeyin.
- Kalan 7 madde ayrı **Tamamlayıcı inceleme** notlarıyla açıklandı. Senin 13 seçimin değiştirilmedi; bu 7 öneri insan κ hesabına katılmadı.
- İki gerçek müşteri görüşmesi hâlâ yapılmadı. Bu kısmı tamamlanmış gösteremeyiz; görüşme formu hazır.


## Sınıfta canlı gösterimi açmak

Proje klasöründe terminali açıp şu komutu çalıştırın:

```sh
.venv/bin/python -m scripts.try_rag
```

`citizen>` satırına şu soruyu yazabilirsiniz:

> Tekerlekli sandalye ile kaldırımdan geçemiyorum. Bildirimde sağlık raporum gerekir mi, hangi bilgiler gerekli?

Kaynak numaralarını ve hangi belge parçasından geldiklerini gösterin. Sonra süre kalırsa şunu sorun:

> What is the exact 2026 fee for a water subscription in Yeşilvadi?

Corpus bu kesin ücreti vermediği için doğru davranış kaynak yetersizliğini belirtmektir. Canlı çıktıyı kontrol etmeden başarılı ilan etmeyin. Her soru bağımsızdır; sohbet geçmişi aktarılmaz. Boş satır veya Ctrl+C ile çıkılır.

Servis sorununda, API kullanmadan canlı kaynak aramasını gösterebilirsiniz:

```sh
.venv/bin/python -m scripts.try_rag --search-only
```

Kayıtlı erişilebilirlik örneğini göstermek için:

```sh
.venv/bin/python -m scripts.try_rag --replay W3-R019
```

Bu son komutun çıktısı **kayıtlı örnek** diye etiketlidir; yeni canlı model cevabı diye sunulmaz. Slayttaki kayıtlı örnek gösterimi zaten açıkça belirtilmiştir. Terminali ayrıca açacaksanız yaklaşık 30–45 saniyelik kısmı slayt anlatımının yerine kullanın; yedi dakikaya eklemeyin.
