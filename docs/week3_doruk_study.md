# Doruk — Week 3 çalışma rehberi

Senin bölümün **7–12. slaytlar**, yaklaşık **2 dakika 20 saniye**. Konun: kaynakları nasıl bulduğumuz, neyi ölçtüğümüz ve eksik kanıtın hangi aşamada oluştuğu.

## Bu hafta neyi değiştirdik?

Beldesk, kurgusal Yeşilvadi Belediyesi için Türkçe ve İngilizce çalışan bir yardımcı. RAG, soruyla ilgili belgeleri bulup bunları cevap modeline kanıt olarak vermek demek.

İlk veri kümesinde vatandaş sorularıyla geliştirici soruları karışmıştı. Örneğin “Model şirket adını tahmin edebilir mi?” yerine artık “Apartmanın tamamında elektrik yok; nereye bildirmeliyim?” gibi hizmet soruları var. Halka açık 30 rehber de vatandaşın başvuru ve takip ihtiyacına göre yeniden yazıldı. İç talimatlar vatandaş rehberi veya ana retrieval sorusu olarak kullanılmıyor.

**Akış:** Belgeler → bölüm parçaları → BM25 ve anlamsal arama → RRF → reranker → yetkili kaynaklar → atıflı cevap → iddia değerlendirmesi.

Belgelerin kurgusal olduğu metadata içinde açık. Bu, gerçek belediye tarifesi veya çalışma saati uydurabileceğimiz anlamına gelmiyor. Belgede olmayan kesin bilgiler için cevap vermemek gerekir. Gerçek kayıt sorgulama, ödeme veya ekip gönderme aracı şu anda bağlı değil.

## 7. slayt — Üç farklı başarı ölçüsü

| Ölçüm | Güncel sonuç | Ne anlama geliyor? |
|---|---:|---|
| Hit@1 | 19/32 = 0.59375 | İlgili bir kanıt ilk sırada mı? |
| Hit@3 | 30/32 = 0.9375 | İlgili bir kanıt ilk üçte mi? |
| Hit@5 | 32/32 = 1.0 | En az bir ilgili kanıt ilk beşte mi? |
| Bütün gerekli kanıt grupları @5 | 31/32 = 0.96875 | Sorunun bütün gerekli parçaları için kanıt var mı? |
| MRR@10 | 0.758854 | İlk ilgili kanıt ne kadar erken geliyor? |

**32/32, “32 doğru cevap” demek değil.** Bir sorunun yalnız yarısını destekleyen belge bulunmuş olabilir. Tam kanıt kapsamı bu yüzden ayrıca ölçülüyor. Üretilen cevabın doğru ve yeterli olması ise başka bir ölçüm.

MRR için ilk ilgili sonuç 1. sıradaysa 1; 2. sıradaysa 1/2; 3. sıradaysa 1/3 puan alınır. İlk 10’da ilgili sonuç yoksa 0 olur. Soruların puanlarının ortalaması hesaplanır. Bu puan, bütün kanıt parçalarının geldiğini göstermez.

Küme **32 cevaplanabilir soru + 6 kontrol** içeriyor. Cevaplanabilir sorular 16 Türkçe / 16 İngilizce; kontrollerle birlikte toplam 19 Türkçe / 19 İngilizce. Altı geliştirme sorusu ayrı. Üç soru birden fazla kanıt grubu gerektiriyor; ikisi farklı hizmetleri birlikte soruyor. Geçerli alternatif kaynaklar ölçümden önce kaydedildi.

## 8. slayt — Ablation

Ablation, bir bileşenin etkisini anlamak için diğer ayarları koruyarak tek şeyi değiştirmek demek.

| Düzenek | Hit@5 | MRR@10 |
|---|---:|---:|
| Hybrid + reranker | 32/32 | 0.758854 |
| Dense + reranker | 32/32 | 0.761458 |
| Hybrid, reranker kapalı | 29/32 | 0.689323 |

İlk karşılaştırmada reranker aynı; yalnız aday bulma yöntemi değişiyor. **Dense’in MRR’ı biraz daha yüksek.** Hybrid daha iyi çıktı dememelisin. İkincide hybrid aynı kalıyor, yalnız reranker kapatılıyor; MRR ve hit@5 daha düşük çıkıyor. Bu küçük, sentetik ve taslak etiketli test evrensel üstünlük kanıtı değil.

## 9. slayt — Scoreboard ve sürüm ayrımı

Haftalık aynı 13 metrik satırı korunuyor. `null`, ölçüm bulunmadığı anlamına gelir; sıfır demek değildir. Kaynak bulma, cevabın kaynağa sadakati ve görevi gerçekten tamamlama farklı şeylerdir.

**Eski 31/32 ve MRR≈0.953 sonuçları emekliye ayrılan v1 kümesine ait.** Belgeler ve sorular değiştiği için yeni MRR≈0.759 ile doğrudan kalite artışı veya düşüşü olarak karşılaştırılamaz. Yeni vatandaş kümesi kendi dosya ve soru hash’leriyle yeniden ölçülür.

Yeni Gemini çalıştırmasının geçerli cevap, iddia ve servis hatası sayılarını final sunumdan oku. V1’deki “38/38 kayıt” ve “61 iddiada sıfır işaret” sayılarını yeni kümenin sonucu gibi anlatma. Önbellekten kullanılan sonuçlarla yeni çağrılar ayrı gösterilir. Süre metriği de kaynak arama ve model hizmet süresidir; planlama/tekrar beklemelerini dışlayan bir değeri kullanıcıya görünen toplam süre sanmamalıyız.

## 10. slayt — Faithfulness

Faithfulness, cevabın verilen kaynağa sadakati. Cevap atomik iddialara ayrılır; her iddia kendi atıf yaptığı kanıtla karşılaştırılır.

Kaynak numarasının var olması veya alıntının kaynakta bulunması, iddianın anlamca desteklendiğini tek başına kanıtlamaz. “Ücret belirtilmemiş” bilgisinden “ücretsiz” sonucu çıkmaz.

- **supported:** Kaynak iddianın bütün önemli kısımlarını destekliyor.
- **unsupported:** Kaynakla çelişki, anlamı değiştirme veya araç sonucu olmadan yapılmış işlem iddiası var.
- **insufficient_evidence:** Kaynak bu ayrıntıyı doğrulamıyor. Bu, gerçek hayatta tersinin doğru olduğu anlamına gelmez.

Son iki etiket toplam desteklenmeyen iddia oranında birlikte sayılır. Geçerli judge kararı yoksa onu desteklenmiş saymıyoruz. Judge oranı, insan tarafından doğrulanmış cevap doğruluğu değildir.

## 11. slayt — R032: Bir kısmı bulundu, tamamı bulunmadı

Vatandaş parkta bir şenlik düzenlemek istiyor; aynı zamanda tekerlekli sandalye kullanıcıları girişten geçemiyor. Soruda iki ihtiyaç var: **etkinlik izni bilgileri** ve **erişilebilirlik sorununun bildirimi**.

Ölçülen hybrid + reranker sıralamasında erişilebilirlik ayrıntısı **3. sırada**, etkinlik başvurusu ayrıntısı **7. sırada**. Cevap modeline yalnız ilk beş parça verildiğinde izin bilgisi dışarıda kalıyor.

Bu yüzden aynı vakada hit@5 başarılı, bütün gerekli kanıt grupları @5 başarısız. Sorun, yeniden sıralama ve ilk beş bağlamın seçimi aşamasında. Kaynak, aday havuzundan tamamen kaybolmuş değil; 7. sırada. Eski R008 gizlilik örneğini burada kullanma. Soruyu veya altın etiketi sonuç güzel görünsün diye değiştirmiyoruz; iyileştirmeyi ayrı geliştirme örneklerinde sınamak gerekir.

## 12. slayt — Hata nerede?

| Durum | Aşama |
|---|---|
| Gerekli kanıt ya da bir soru parçasının kanıtı bulunamadı | Retrieval / bağlam seçimi |
| Kanıt var ama cevap onun desteklemediği şeyi söylüyor | Generation |
| Model hizmeti cevap vermedi, örneğin HTTP 503 | Sağlayıcı / erişilebilirlik |
| Judge çalışmadı veya geçersiz çıktı verdi | Evaluation |

Bu ayrım hangi bileşeni düzelteceğimizi gösterir. API hatasını halüsinasyon oranına karıştırmıyoruz.

## Bilmen gereken kavramlar

- **Corpus:** 30 halka açık hizmet rehberi + 1 personel erişim testi belgesi. Yeni halka açık metinler vatandaşlara hitap ediyor.
- **Chunk:** Belgenin parçası. Bu sürümde 92 bölüm/parça var. 140 kelime sınırı ve uzun bölümlerde 20 kelimelik örtüşme kuralı var; mevcut bölümler kısa olduğundan fiilî örtüşme sıfır.
- **BM25:** Kelime eşleşmesiyle arama.
- **Embedding / dense:** Anlamı temsil eden sayısal vektörlerle arama. E5 modeli yerelde çalışıyor.
- **RRF:** İki arama yönteminin sıralamalarını sıra konumlarından birleştirme.
- **Reranker:** Soru ile aday parçayı birlikte okuyup yeniden puanlama.
- **Access filter:** Vatandaşa kapalı personel belgesi sıralama öncesinde çıkarılır. Kullanıcının mesaja “yöneticiyim” yazması yetki vermez.
- **Cohen’s κ:** İnsan ile judge uyumu; yanında gerçek eşleşme sayısı yazılmalı. Tek bir değer judge’ın her soruda doğru olduğunu kanıtlamaz.

## Tamamlanmış insan incelemesi ve görüşmeler

Ekip **20 insan etiketini tamamladı**. Tarihsel kontrol kümesinde **17/20 karar aynı**, κ≈**0.771**. Bu iddialar eski corpus’un o sırada kaydedilmiş kaynak metinlerini kullanıyor. Tamamlanmış bu çalışma korunuyor; yeni vatandaş sorularının veya cevaplarının insan doğruluğu diye sunulmuyor.

**İki müşteri görüşmesi de tamamlandı.** Bunları hâlâ eksikmiş gibi anlatma. Buna karşılık yeni yazılan **30 halka açık rehberin yeni sürümü için insan onayı 0/30**. Önceki su rehberine verilmiş onay, değiştirilmiş metne otomatik geçmez. Yeni kaynaklar ve gold kanıtlar ayrıca incelenmeli.

## Canlı gösterim komutları

Proje klasöründeki terminalde:

```sh
.venv/bin/python -m scripts.try_rag
```

`citizen>` satırına şu doğal soruyu yazabilirsin:

> Yeni taşındığım evde kiracıyım. Su aboneliğini üzerime almak için ne hazırlamalıyım? Önceki abone numarasını bilmiyorum.

Atıfları ve hangi belge parçasından geldiklerini göster. Cevabı okumadan doğru ilan etme. İkinci örnek olarak belgelerde bulunmayan kesin bir ücret sorulabilir:

> What is the exact 2026 fee for a water subscription in Yeşilvadi?

Doğru davranış, yeterli kaynak olmadığında sabit yanıtı vermek. Her soru bağımsızdır; önceki sohbet geçmişi aktarılmaz. Boş satır veya Ctrl+C ile çıkılır.

API olmadan canlı yerel arama:

```sh
.venv/bin/python -m scripts.try_rag --search-only
```

Final çalıştırmadan kaydedilmiş su aboneliği örneği:

```sh
.venv/bin/python -m scripts.try_rag --replay W3-R003
```

Replay kayıtlı örnektir; yeni canlı model cevabı değildir. Slayttaki kayıtlı gösterim de bu şekilde etiketlidir. Terminali ayrıca kullanırsanız 30–45 saniyeyi slayt anlatımının yerine koyun; yedi dakikaya eklemeyin.

## Gelebilecek sorulara kısa cevaplar

**“32/32 ise neden eksik kanıt var?”** Hit@5 en az bir ilgili kanıtı bulmayı ölçer. R032’de iki ihtiyaçtan yalnız birinin kanıtı ilk beşte; bütün gerekli kanıt kapsamı 31/32.

**“Hybrid daha mı iyi?”** Bu testte hayır. İkisinin hit@5’i aynı; dense MRR’ı biraz daha yüksek. Hybrid’in evrensel üstünlüğünü iddia etmiyoruz.

**“Yeni MRR niye eskisinden düşük?”** Ölçülen soru ve belgeler değişti. Eski iç kural sorularıyla yeni vatandaş soruları aynı test değil.

**“κ≈0.771 yeni cevapların doğruluğu mu?”** Hayır. Eski kaynak görüntüleriyle yapılan 20 etiketlik tarihsel judge uyumu.

**“Neyi sırada iyileştireceğiz?”** Yeni kaynak ve kanıt etiketlerini bağımsız inceleme; kontrollü araç sonuçlarını ölçme; çok adımlı görev başarısını ölçme. Kaynak onayını 0/30’dan artırmak ile araç/görev oranlarını ölçülebilir hâle getirmek ayrı hedefler.
