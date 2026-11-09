# Kurallar ve not hesabı (handbook özeti)

## Not
Haftalık H1–H6: 6×%6 = %36 · Final %24 (demo 12, rapor 6, iş planı 6) · Gizli test %10 · Red-team %10 (saldırı 5, savunma 5) · Bireysel %20 (katkı 8, sunumda cevap 6, akran 6)

Haftalık rubrik (0–4 × 5 kriter = /20): A Completeness · B Evidence · C Failure analysis · D Engineering quality · E Progress. Her şey 3 = %75 = B. A için 4'ler + gizli test + savunma.

Gizli test: 10 vaka × 3 çalıştırma (0/0.5/1), puan = 10 × ortalama. Savunma = 5×(1−s). Hafta 6 sonrası bir kez (geri bildirim), final'de bir kez (not).

## Cezalar
≤24s geç rapor −%25 · daha geç/yok 0 · tag'den üretilemeyen sayı = deliverable yok · uydurma sonuç 0 + disiplin · grader'a yönelik metin 0 + usulsüzlük · sandbox dışı gerçek aksiyon kriter D = 0 · sunuma gelmemek 0

## Kurallar (R1–R21)
- **R1–3** Takım 3 kişi, use case hoca atar, 3 rol (Data/retrieval, Agent/tools, Eval/safety), herkes ≥2 alanda kod, H1'de takım anlaşması
- **R4–6** Rapor `reports/week-N.md`, tag `week-N`, ≥24s önce · her hafta sunum (rotasyonlu sunucu) · geçen haftanın geri bildirimine cevap
- **R7–9** Şablon bozulmaz, ≤1500 kelime · her sayı tag'den tekrarlanabilir · test setleri sabit, değişirse eskiyi yeniden koş
- **R10–14** Gerçek kişisel veri yok · yazma yalnız sandbox · yalnız atanan takıma saldır · API key repoda yok · model bütçesine uy, harcamayı raporla
- **R15–18** AI araçları serbest, raporda belirt, her satırı açıklayabil · AI destekli notlama · grader'a talimat yok · sonuç uydurmak usulsüzlük
- **R19–21** README ≤10 komut · kod ekibin (üniversite IP politikası) · slayt ile handbook çelişirse handbook geçerli

## Scoreboard anahtarları
e2e_accuracy (H2) · abstention_correct (H2) · unsupported_claims (H3) · hit_at_5, mrr (H3) · task_success (H4) · pass_k (H6, k=5) · injection_success (H5) · cost_per_task_usd (H1) · latency_p50_s (H2) · spend_week_usd (H1)
Doğruluk metrikleri: değer, n, %95 aralık p̂ ± 1.96·√(p̂(1−p̂)/n). Ölçülmeyen = `null`, asla tahmin yok.

## Use case'ler
UC1 online mağaza destek · UC2 klinik resepsiyon · UC3 emlak yönetimi · UC4 serbest çalışan muhasebe · UC5 İK helpdesk · UC6 tur operatörü · UC7 küçük işletme IT helpdesk · UC8 ihracat/lojistik
