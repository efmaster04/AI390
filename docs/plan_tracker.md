> Internal planning note (Turkish), not a deliverable. Superseded where it conflicts with the Beldesk documents.
# Plan takibi (deliverable ID → durum → kanıt)

Kural: kanıtı olmayan deliverable "yapılmadı" sayılır. Durum: ☐ yok · ◐ kısmi · ☑ tamam

## Hafta 1 — Problem ve baseline (scoreboard: cost per request)
- ☑ W1.1 Takım anlaşması (roller, toplantı, karar kuralı, teslim edilmezse ne olur, ders sonrası sahiplik) → `docs/team_agreement.md`
- ☑ W1.2 Use case brief (ilk müşteri, persona, 5 user story, kapsam içi/dışı) → `docs/use_case_brief.md`
- ☑ W1.3 25 gerçekçi kullanıcı girdisi (soru, sorgu, aksiyon, cevaplanamaz, çok adımlı etiketli) → `eval/testsets/week1_inputs.jsonl`, `docs/test_set_week1.md`
- ☑ W1.4 Veri envanteri (dokümanlar, tablolar/kolonlar, aksiyon API taslağı, güvenilmez girdi kaynakları) → `docs/data_inventory.md`, `data/structured/schema.sql`
- ☑ W1.5 Baseline: tek prompt, 25 girdi, sıcaklık 0 / 0.7 / 1.2 → `eval/results/week1/`, `docs/baseline_analysis_week1.md`
- ☑ W1.6 Maliyet tahmini (request başı token, 1000 request $; formül + varsayım) → `eval/results/week1/cost_summary.json`, `scripts/cost_estimate.py`
- ☑ W1.7 ≥5 öngörülen hata (Module 1 kavramlarına bağlı) → `docs/predicted_failures.md`
- ☑ W1.8 Repo + README, tag `week-1` → `README.md`, tag `week-1`
- ☑ Ek: use case tercih formu / özel use case onayı (Beldesk)

## Hafta 2 — Prompt ve eval harness (accuracy ± belirsizlik, abstention)
- ☑ W2.1 Request classifier (JSON şema, T=0, doğrulama + retry) → `src/classifier/`, `prompts/classifier_v1.md`
- ☑ W2.2 Ana prompt (6 yapı taşı, versiyonlu şablon) → `prompts/assistant_v3.md`, `docs/prompt_design_week2.md`
- ☑ W2.3 ≥40 vakalık test seti (≥5 cevaplanamaz, ≥5 adversarial, ≥5 edge) → `eval/testsets/week2_cases.jsonl`, `docs/test_set_week2.md`
- ☑ W2.4 Eval harness (tek komut, scoreboard dosyası yazar) → `src/eval_harness/run.py`, `eval/results/week2/scoreboard.json`
- ☑ W2.5 3 prompt versiyonu karşılaştırması (%95 aralık + McNemar) → `eval/results/week2/prompt_comparison.md`, `eval/results/week2/prompt_comparison.json`
- ☑ W2.6 LLM judge, 20 insan etiketine karşı Cohen's κ → `src/eval_harness/judge.py`, `eval/testsets/week2_human_labels.jsonl`, `eval/results/week2/judge_calibration.json`
- ☑ W2.7 Halüsinasyon günlüğü (≥10 örnek, tip ile) → `docs/hallucination_log_week2.md`, `eval/results/week2/hallucination_log.json`
- ☑ W2.8 3 doğrudan injection denemesi → `docs/injection_test_week2.md`, `eval/results/week2/injection_test_results.json`

## Hafta 3 — RAG (hit@k, MRR, unsupported claims)
- ☐ W3.1 ≥30 doküman corpus, metadata (kaynak, tarih/versiyon, erişim)
- ☐ W3.2 Chunking seçimi + gerekçe
- ☐ W3.3 Hibrit arama (BM25 + embedding, RRF) + reranker
- ☐ W3.4 Numaralı atıflı cevaplar, dokümanda yoksa sabit cevap
- ☐ W3.5 ≥30 soruluk retrieval testi (hit@1,3,5,10 + MRR)
- ☐ W3.6 Faithfulness (iddia bazlı, judge insan etiketine karşı)
- ☐ W3.7 2 ablation (tek değişiklik)
- ☐ W3.8 Hata analizi (retrieval mı generation mı)
- Ürün: ≥2 potansiyel müşteriyle konuş

## Hafta 4 — Araçlar ve agent loop (task success, steps, cost/task)
- ☐ W4.1 ≥3 araç (doküman arama, veri sorgu, 1 yazma)
- ☐ W4.2 Agent loop (adım/token/süre limiti, tekrar çağrı tespiti)
- ☐ W4.3 Context yönetimi
- ☐ W4.4 ≥10 çok adımlı görev + trace
- ☐ W4.5 Cost per task vs context-growth formülü
- ☐ W4.6 Tasarım notu (tek çağrı / workflow / agent)
- ☐ W4.7 Yazma aksiyonu yalnız sahte API'de
- Her öğrenci: 1. akran değerlendirmesi (Ek B)

## Hafta 5 — MCP ve güvenlik (injection success rate)
- ☐ W5.1 MCP server (SDK'nın spec revizyonunu belirt)
- ☐ W5.2 Standart MCP host'ta demo
- ☐ W5.3 Lethal trifecta analizi + araç risk kademeleri
- ☐ W5.4 Her yazma için onay adımı
- ☐ W5.5 Red-team saldırı (≥5 saldırı, atanan takıma + hocaya rapor)
- ☐ W5.6 Red-team savunma (öncesi/sonrası başarı oranı)
- Ürün: fiyat hipotezi

## Hafta 6 — Agent eval ve sertleştirme (pass^5, latency)
- ☐ W6.1 Sandbox (sahte araçlar, sıfırlanabilir durum)
- ☐ W6.2 ≥20 agent görevi (beklenen son durum, yasak aksiyonlar, bütçe)
- ☐ W6.3 Her görev 5 kez (success, pass^5, steps, cost, latency)
- ☐ W6.4 En kötü 3 hata düzeltildi (önce/sonra)
- ☐ W6.5 Gizli test komutu (dosyadan görev okur, dosyaya sonuç yazar)
- ☐ W6.6 Regresyon kontrolü

## Hafta 7 — Final
- ☐ F1 Canlı demo (hocanın seçtiği görevler)
- ☐ F2 Final rapor (≤4000 kelime, Ek A)
- ☐ F3 1 sayfalık iş planı
- ☐ F4 Repo tag `final`, README ≤10 komut
- ☐ F5 2. akran değerlendirmesi
