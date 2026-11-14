# Beldesk ana asistan prompt'u (W2.2)

Ablation amaçlı üç sürüm; W2.5'te aynı 42 vakalık setle (`eval/testsets/week2_cases.jsonl`) karşılaştırılacak.

## Altı yapı taşı

Ders listesi elimizde olmadığı için standart liste kullanıldı:
1 Role, 2 Task/Instructions, 3 Context, 4 Constraints/Rules, 5 Examples (few-shot), 6 Output format.

| Blok | v1 | v2 | v3 |
|---|---|---|---|
| Role | ✓ | ✓ | ✓ |
| Task | ✓ | ✓ | ✓ |
| Context | – | ✓ | ✓ |
| Constraints | – | ✓ | ✓ (+ enjeksiyon savunması) |
| Examples | – | – | ✓ (4 örnek) |
| Output format | ✓ | ✓ | ✓ |

## Sürümler arası fark ve hipotez

| Sürüm | Önceki sürüme eklenen | Azaltması beklenen hata |
|---|---|---|
| v1 | Baseline'ın yapılandırılmış hali (Role, Task, Output format) | Biçim tutarsızlığı, dil karışması; uydurma ve yapılmamış işlem hâlâ beklenir |
| v2 | Context (kapsam, P1–P4 özeti, RAG/DB/araç yok) + Constraints | Uydurma (ücret, saat, telefon), yapılmamış işlem ("kaydınız oluşturuldu"), gizlilik ihlali; abstention artmalı, acilde 112 ilk cümlede |
| v3 | Enjeksiyon savunması + 4 few-shot (taslak onayı, cevaplanamaz soru, enjeksiyon, acil durum) | Enjeksiyon başarısı (Week 1: 3/3), kalan yapılmamış işlem ifadeleri; abstention ifadesinin tutarlılığı |

Her sürüm bir öncekinin metnini kelimesi kelimesine içerir; yalnız yeni bloklar eklenir (satır bazlı diff yalnız ekleme gösterir). Bloklar kanonik sırada durduğundan yeni bloklar Output format'tan önceye girer. Few-shot örnekleri test setindeki hiçbir metinle cümle ya da 6-gram paylaşmaz.

## Yeni sürüm ekleme kuralı

1. Son sürümü kopyala (`v3.md` → `v4.md`).
2. Front matter'da `version`, `date`, `parent` (önceki sürüm) ve tek cümlelik `change` alanını güncelle; `blocks` listesini düzelt.
3. Eski sürüm dosyalarını asla değiştirme; düzeltme gerekiyorsa yeni sürüm aç.
4. Ablation için tek seferde tek değişken değiştir ve her koşuda prompt sürümünü kaydet.
