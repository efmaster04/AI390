# AIC390 Prompt Engineering Projesi

Hoca: Huseyin Ulusoy · Kaynak: `../Prompt_Engineering_Project_Handbook.pdf`
Use case: _(atanınca doldur; tercih taslağı: `docs/use_case_preference.md`)_ · Ürün adı: _(H1'de seç)_ · Ekip: _(doldur, 3 kişi)_
Model sağlayıcı: Claude API (Anthropic) · API anahtarı `.env` içinde, repoya girmez (R13)

## Mimari (7 katman)
1 Understand (classifier, JSON) → 2 Answer (RAG) → 3 Look up (veri aracı) → 4 Act (yazma aracı + onay) → 5 Connect (MCP) → 6 Orchestrate (agent loop) → 7 Measure (eval + scoreboard)

## Klasörler
| Yol | İçerik |
|---|---|
| `src/classifier` `src/rag` `src/tools` `src/agent` `src/mcp_server` | Katmanlar |
| `data/corpus`, `data/structured` | Sentetik dokümanlar ve tablolar (R10: gerçek kişisel veri yok) |
| `sandbox/` | Sahte API, sıfırlanabilir durum (R11) |
| `eval/` | Test setleri ve scoreboard scriptleri (R8, R9) |
| `reports/week-N.md` | Haftalık rapor (şablon: `docs/weekly_report_template.md`) |
| `docs/` | Plan takibi, kurallar, scoreboard geçmişi |

## Kurulum (en fazla 10 komut, R19)
_(H7'ye kadar doldurulacak)_

## Kurallar kısaca
API anahtarları repoya girmez (`.env`, R13). Her sayı tag'li commit'ten script ile üretilebilmeli (R8). Rapor, ders saatinden en az 24 saat önce `week-N` tag'iyle teslim (R4).
