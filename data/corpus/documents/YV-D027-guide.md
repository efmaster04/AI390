---
{"doc_id":"YV-D027","title":"Yeşilvadi Tekrarlanan Bildirim ve Güncelleme İlkeleri","title_en":"Duplicate Reports and Updates Guide","language":"tr","version":"0.1-draft","updated_at":"2026-11-24","source":"beldesk://synthetic/YV-D027","access":["public"],"synthetic":true,"review_status":"draft","keywords":["duplicate","update","tekrar bildirim","güncelleme"]}
---

# Yeşilvadi Tekrarlanan Bildirim ve Güncelleme İlkeleri

## Kapsam ve veri niteliği {#scope}

Bu doküman, AIC390 Beldesk projesindeki kurgusal Yeşilvadi için ekip tarafından incelenmek üzere hazırlanmış sentetik taslaktır. Gerçek belediye mevzuatı veya hizmet taahhüdü değildir. Bu belgenin okunması herhangi bir kayıt, ödeme, rezervasyon ya da saha müdahalesi oluşturmaz.

## Tekrar ile yeni olay ayrımı {#details}

Aynı olaya ilişkin yeni mesaj, başka bir arıza olduğu varsayımıyla otomatik yeni kayıt sayılmaz. Varsa önceki referans ve olayın konumu öğrenilir. Bildirimlerin aynı olay olduğuna karar vermek için veritabanı ve uygulama kuralları gerekir; bu sürüm bunlara sahip değildir. Tek kişinin tekrar yazması daha fazla kişinin etkilendiğinin kanıtı değildir.

## Zaman ve yeni kanıt {#limits}

Birleştirme ileride uygulanırsa ilk kayıt zamanı korunmalı, güncelleme geçmişi kaybolmamalıdır. Yeni tehlike veya daha geniş etki bildirilmesi ise yeniden değerlendirmeye konu olabilir. Beldesk mevcut sürümde kayıt birleştirdiğini, sınıfı sistemde yükselttiğini veya önceki kaydı bulduğunu söylemez. Süre metni tek başına doğrulanmış bir takvim tarihi olarak sunulmamalıdır.
