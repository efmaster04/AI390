# Use case tercih formu (Ek C) — taslak

Takım olarak ilk seansta teslim edilir. Hoca takım başına bir use case atar, mümkünse tercihlerden birini.

| Sıra | Use case | Neden bu? (tek cümle) |
|---|---|---|
| 1. tercih | UC2 Klinik resepsiyon asistanı | Tıbbi alan bilgisi var; "doğru reddetme" bir özellik olduğu için abstention, escalation ve güvenlik metriklerini anlamlı ölçebiliriz. |
| 2. tercih | UC7 Küçük işletmeler için IT helpdesk | Hata kodları ve ürün adları hibrit aramayı doğal kılıyor; şifre sıfırlama aracı injection ve red-team için zengin bir hedef. |
| 3. tercih | UC6 Tur operatörü rezervasyon asistanı | Türkçe/İngilizce çok dilli arama ve tarih/fiyat kesinliği; yerel pazar bilgisi (Kapadokya vb.) bir avantaj. |

## Takım üyeleri (doldurulacak)
| Üye | Öğrenci no | Planlanan rol |
|---|---|---|
| | | Data and retrieval lead |
| | | Agent and tools lead |
| | | Evaluation and safety lead |

## Alan deneyimi (opsiyonel)
_(Takımda klinik, mağaza, turizm, IT gibi bir alanda çalışmış biri varsa yaz.)_

---
## Tercih mantığı (iç not)
- Tüm use case'ler aynı 8 bileşeni içeriyor; ders notu açısından fark küçük. Seçim **alan bilgisi** ve **zorluk profiline** göre.
- UC2: en sıkı güvenlik gereksinimi (tıbbi tavsiye yok, acil durum yönlendirme). Riski: sınır vakaları tanımlamak emek ister.
- UC7: teknik olarak en kolay başlanan; hata kodları BM25'in neden gerektiğini net gösterir.
- UC6: çok dilli test seti hazırlamak ek iş; tarih ve fiyat tool'dan gelmeli.
- Kaçınılan: UC4 (yıllık değişen vergi kuralları ve versiyonlu corpus yükü), UC8 (HS kodu verisi hazırlamak zor).
