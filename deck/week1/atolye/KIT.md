# KIT v3 — sahne sözleşmesi (Beldesk Week 1 canlı deck, "maskotun dünyası")

Önce `atolye/sozlesme.md` (pano haritası v3, kalite çıtası, yasaklar). Bu dosya NASIL yazılacağını söyler.
Referans sahneler (kaliteyi bunlar belirler): `cover.html`, `demo-memory.html` (terminal + çok adım + poz değişimi),
`questions.html` + `q-measurement.html` / `q-failure.html` / `q-priority.html` (hotspot + dal, veri kartı, damga).
**Ton ayarı (sözleşme "Ton ayarı", kullanıcı: "çok çocuk gibi, biraz ciddileştir") kitin varsayılanlarına işlendi; §0 kurallarına uy.**

## 0. Ton: karakterli ama olgun editoryal sayfa (kit varsayılanları bunu yapar; sahnede bozma)
Kontrol sorusu her kare için: "çocuk kitabı sayfası mı, iyi tasarlanmış teknik sunum sayfası mı?" İkincisi; ama beyaz/gri kurumsal şablona DÖNME.
- **Süs:** `.bk-spark` / `.bk-burst` slayt başına en fazla 2 küçük öğe ve yalnız anlamlı anda (damga vurulunca, sayı tamamlanınca). Konfeti yok. Maskot çiziminde parıltı/spiral varsa (unutkan, selam, gorevli) ek süs koyma.
- **Eğim:** panel, kart, zarf, terminal, callout 0°. `slam`'e `rotation` verme. Yalnız damga (`stamp` vars. -3°, en fazla ±3°) ve tek bir ataşlı not (`.bk-panel--tilt-*` = ±1°) eğik olabilir.
- **El yazısı (Caveat, `.bk-note`):** slayt başına EN FAZLA 1 not, ≤ 4 kelime, ünlemsiz. Diğer açıklamalar `.bk-note--plain` (gövde fontu, 30 px, düz) ya da `.bk-label`.
- **Başlık:** `--fs-title` 64 px (bir kademe küçüldü). Sarı fosfor (`bk-scan`) yalnız TEK kilit ifadenin altında; tüm başlık/cümle boyanmaz.
- **Maskot:** büyük (`--h` 520–580) yalnız cover, demo-memory, demo-pothole, questions. Diğerleri `.bk-mascot--aide` (300 px; aralık 260–340), köşede, içerik alanının ≤ %15'i. Tepki tek ve kısa (hop 20 px).
- **Renk dozu:** zemin + krem panel baskın; sarı/teal/kırmızı vurgu (sekme, sol kenar çizgisi, şerit, damga, çubuk). Büyük düz sarı/kırmızı/teal blok YOK: `.bk-panel--sun` artık krem + üst sarı şerit; kırmızı/teal anlamı için krem panel + `border-left: 16px solid var(--tomato|--teal)` ya da renkli `.bk-tab` kullan. `.bk-panel--teal/--tomato` (soft dolgu) yalnız küçük öğede.
- **Kontur:** `--stroke` 4 px, `--offset` 7 px; küçük öğelerde 3 px. Sahnede 5+ px kontur yazma.
- **Veri:** rakam, tablo, formül, çubuk net ızgarada; hizalar kesin; eksen/etiket/birim eksiksiz. Önce veri görünür, sonra maskot.
- **Hareket:** "kendinden emin": `EASE.slam` back.out(1.15), `pop` back.out(1.5), maskot inişi back.out(1.2); elastic/bounce/yoyo YOK. Her adımda yine ≥ 2 öğe hareket eder.
- **Dil:** kısa, kesin, profesyonel İngilizce; "oops", ünlem, sevimli ifade yok ("not sent!" → "not sent").

## 1. Düzen ve kim neye dokunur
```
week1/index.html              ÜRETİLİR (birlestir.mjs) — canlı kap
week1/vendor/                 player/slideshow/runtime (dokunma)
composition/index.html        ÜRETİLİR — ada + host'lar (ELLE DÜZENLEME)
composition/assets/kit/       kit.css, kit.js, gsap.min.js, grain.png, qr-repo.svg (dokunma)
composition/assets/fonts/     Fraunces 700/900, Nunito 400/700/800, JetBrains Mono 400/700, Caveat 700 (latin+latin-ext)
composition/assets/maskot/    9 poz, şeffaf, görünür sınıra kırpılı PNG (orijinaller week1/assets/maskot/)
composition/scenes/<id>.html  ← SAHNE AJANI YALNIZ BUNU YAZAR (+ atolye/teslim-<ad>.md)
atolye/deck.json              sıra, no, tag/tagName, repo, mascot, başlık, notlar, hotspot (şef)
```
Senin dosyan `STUB / <id>` yer tutucusudur (bandı, W1.x etiketi, repo satırı ve maskotu deck.json'dan hazır); baştan yaz.

## 2. Sahne iskeleti (birebir bu kalıp)
```html
<template id="<id>-template">
  <style>
    #root { position: absolute; inset: 0; }
    [data-composition-id="<id>"] .<id>-grid { ... }      /* her kural bu önekle; id'ler <id>- önekli */
  </style>
  <div id="root" data-composition-id="<id>" data-hold data-width="1920" data-height="1080"
       data-window="8" data-fragments="1.4,2.5,3.6">
    <div class="bk-stage">
      <div class="bk-sheet"></div>
      <header class="bk-band">
        <span class="bk-deliv"><span class="bk-deliv-id">W1.3</span>25 user inputs</span>  <!-- teslimat slaytı -->
        <!-- teslimat değilse: <span class="bk-folio">BELDESK / SCOREBOARD</span> -->
        <span class="bk-section">W1.3</span>
        <span class="bk-no">06 / 22</span>   <!-- deck.json "no" ile aynı; slayt sayısı değişirse şef günceller -->
      </header>
      <div class="bk-rule"></div>
      <h2 class="bk-title">The 25-case set covers the full workflow</h2>
      ... mutlak konumlu bloklar ...
      <div class="bk-repo"><span class="bk-repo-k">repo</span>docs/test_set_week1.md</div>   <!-- teslimat slaytı -->
      <div id="<id>-mascot" class="bk-mascot bk-mascot--aide bk-mascot--buyutec"><img class="bk-mascot-pose" src="assets/maskot/buyutec.png" alt=""></div>
    </div>
  </div>
  <script>
    BK.scene("<id>", function (tl, root, BK) {
      BK.frame(tl, root, 0);                 // bant + çizgi + başlık + repo satırı (ilk satır)
      BK.mascotIn(tl, "#<id>-mascot", 0.25); // her slaytta
    });
  </script>
</template>
```
- `data-window` = sahnenin süresi (sn). Birleştirici okur, pencereleri art arda dizer. Fragment'lar `< window - 0.3`.
- Renk yalnız token (`var(--ink)` …), font yalnız `var(--font-display|body|mono|hand)`. Hex, `@font-face`, `<link>` YOK.
- Kaynak dışı metin/rakam yok (`icerik.md` + `docs/presentation_week1.html`). El yazısı notları kısa ve kaynaktan türetilmiş olur.
- Okunan yazı ≥ 40 px, terminal/kod ≥ 34, etiket ≥ 28. `.bk-small` (32), `.bk-bar-label` (32), `.bk-check-path`, `.bk-fx-k`, `.bk-label`, `.bk-note--plain` (28–32) YALNIZ etiket/dipnot içindir; seyircinin okuyacağı cümle bunlarla yazılmaz. Kenar ≥ 56 px (sağ/sol 96, alt öğe ≤ y 1000). Başlık 2 satıra inerse gövde y ≥ 340.
- Bilerek üst üste binen öğeye (terminal üstü zarf, kart üstü not) `data-layout-allow-overlap`.

## 3. Görsel dil (kit.css)
Token (maskot PNG'lerinden ölçüldü): `--paper #fae1b6` zemin · `--bg #e8c58f` sayfa kenarı (+halftone) · `--cream #fff6e0` panel ·
`--ink #161310` kontur/yazı · `--ink-2` ikincil yazı · `--sun #fec835` dikkat · `--tomato #e34b24` sorun (yazıda `--tomato-ink`) ·
`--teal #38ac9d` iyi/ölçüldü/sistem (yazıda `--teal-ink`) · `--shadow #b19f81` · `--blush #ee8e69`. Anlam sabit: kırmızı=sorun, teal=iyi, sarı=vurgu.

| Sınıf | Ne |
|---|---|
| `.bk-stage .bk-sheet .bk-band .bk-folio .bk-section .bk-no .bk-rule .bk-title` | çerçeve: kontürlü kağıt sayfa, gren, sekme, numara çıkartması, kesikli çizgi, Fraunces 900 başlık |
| `.bk-deliv` > `.bk-deliv-id` | W1.x teslimat etiketi (sarı, delikli kağıt etiket; bandın solunda, folio yerine) |
| `.bk-repo` > `.bk-repo-k` | repo yolu satırı (sol alt köşe) |
| `.bk-panel` + `--sun/--teal/--tomato/--paper/--flat/--tilt-l/--tilt-r` | krem kağıt, 4 px kontur, 7 px ofset düz gölge; `--sun` = krem + üst sarı şerit; `--tilt-*` ±1° (yalnız tek ataşlı not) |
| `.bk-tab` + `--sun/--teal/--tomato` | panelin üst kenarına oturan kağıt sekme |
| `.bk-halftone` (`--sun`, `--tomato`) | halftone nokta deseni (panel arkasına ayrı öğe; konum/boyut sahne verir) |
| `.bk-stamp` + `--teal/--ink/--sun/--muted`, `--on-cream` | çift çizgili damga (vars. kırmızı; krem panel içinde `--on-cream`) |
| `.bk-scan` + `--sun/--teal/--tomato`, `--full`, `--*-solid` | fosforlu kalem (alt %70); koyu zeminde `--full --teal-solid` |
| `.bk-note` + `--teal/--ink/--on-dark`, `--plain` | el yazısı not (Caveat 48 px, -2°; slaytta ≤ 1, ≤ 4 kelime) · `--plain`: gövde fontu 30 px düz etiket |
| `.bk-term .bk-term-bar .bk-term-body .bk-term-line .bk-term-you .bk-term-bot .bk-term-meta .bk-term-en .bk-caret` | terminal penceresi; EN satırı `<b>EN</b>` çipiyle |
| `.bk-bigfig` > `.bk-bigfig-n` `.bk-bigfig-l` | büyük rakam kartı (168 px) |
| `.bk-bars` > `.bk-bar` > `.bk-bar-label .bk-bar-track>.bk-bar-fill(--b/--c/--ink/--dots) .bk-bar-val` | karşılaştırma çubuğu; genişlik `style="--w:52%"` |
| `.bk-check` > `.bk-check-box>.bk-check-tick(--miss) .bk-check-text>.bk-check-path` + `.bk-stamp` | kontrol listesi satırı |
| `.bk-string` (SVG, `--ink/--teal`) + `.bk-pin` | kart-ip-kart bağlantısı |
| `.bk-formula` > `.bk-fx(--sun/--teal)>.bk-fx-v .bk-fx-k`, `.bk-op` | adım adım formül |
| `.bk-tree` (iç içe `ul`, `.is-dir`, `.is-key`) | dosya ağacı (çizgiler CSS; kutu karakteri yok) |
| `.bk-mascot` (`--h`) + `--aide` / `--hero` + `--<poz>` > `.bk-mascot-pose` | maskot kutusu; pozlar üst üste, alta ortalı. Poz sınıfı `--ar`'ı verir (aşağıdaki tablo) |
| `.bk-spark(--teal/--tomato/--ink, --s/--l)` `.bk-burst(--tomato/--sun/--teal)` `.bk-tape` `.bk-callout` `.bk-quote(--teal)` `.bk-code` `.bk-arrow` `.bk-line` `.bk-dot` | süs (≤ 2/slayt) + yardımcı. `.bk-callout` = krem şerit + solda sarı çizgi; `.bk-code` 36 px (okunan kod ≥ 34) |

**Maskot poz oranları** (kırpılı PNG en/boy; `--ar` yanlışsa `object-fit` genişliğe sığar ve karakter `--h`'den kısa çıkar — `--h` yalan söyler). Poz sınıfı (`bk-mascot--yaziyor` …) bunu otomatik verir; `--ar` elle yazma. Kutu genişliği = `--h × --ar`; sağ kenar ≤ 1864 px olsun.

| poz | buyutec | dusunen | gorevli | isaret | mahcup | saskin | selam | unutkan | yaziyor |
|---|---|---|---|---|---|---|---|---|---|
| `--ar` | .88 | .73 | .84 | 1.01 | .82 | .78 | .85 | .90 | 1.04 |

Bir kutuda iki poz varsa (mascotSwap) ilk pozun sınıfını ver; ikinci poz `contain` ile sığar.
| `.bk-label .bk-h3 .bk-lead .bk-small .bk-mono .bk-display .bk-hand .bk-muted .bk-num .t-red .t-teal` | yazı |

## 4. Hareket yardımcıları (window.BK — hepsi fromTo, seek güvenli)
Kural: `from()`, `repeat:-1`, `yoyo`, zamanlayıcı, `Date.now`, `Math.random`, onUpdate ile DOM yazma YOK. GSAP'ın oynattığı öğeye CSS `transform`
yazma (eğim için CSS `rotate` serbest).
**Ön gizleme kuralı:**
1. Bir öğe yalnız bir kez oynuyorsa ön gizleme GEREKMEZ: her yardımcı fromTo ile başlangıç durumunu kurulumda basar, öğe baştan gizlidir (demo-memory'de `#dm-env1`, `#dm-strike`, `#dm-take` böyle). `stamp`, `formula`, `note`, `bars`, `check`, `string`, `burst`, `scan`, `termMark`, `mascotSwap`, `type`, `stream`, `count` `later` seçeneği almaz ve almasına gerek yok.
2. `{later:true}` yalnız AYNI öğenin AYNI özelliğine İKİNCİ tween'de kullanılır (`slam`, `rise`, `fade`, `travel`); `dim`, `mascotReact` zaten `immediateRender:false`.
3. İçinde ayrı oynayan öğeler olan bir KABI sonraki adıma saklamak için: `BK.fade(tl, kap, 0, {from:0,to:0,duration:.01})`, sonra `BK.fade(tl, kap, t, {later:true})` (demo-memory `#dm-turn2`).

| İmza | Etki · örnek |
|---|---|
| `frame(tl, root, 0)` | bant çarpar, çizgi çizilir, başlık kelime kelime oturur, repo satırı kayar |
| `slam(tl, sel, at, {rotation, spin, y, stagger, duration, later})` | kısa iner, çok az taşar, oturur (vars. son eğim 0; `rotation` verme) · `BK.slam(tl, $(".x-card"), .3, {stagger:.1})` |
| `panelIn(...)` | = slam (v1 adı) |
| `rise / fade / dim / draw / travel / titleIn` | v1 ile aynı imza |
| `stamp(tl, sel, at, {rotation, stagger, shake})` | damga vurma: büyükten sert iner + tek geri tepme (~0.4 sn); vars. -3°, en fazla ±3° · `BK.stamp(tl, "#x-done", 2.6, {rotation:3})` |
| `count(tl, el, to, at, {from, duration, decimals})` | sayar; öğe yalnız rakamı tutar · `BK.count(tl, "#x-n", 75, .4)` |
| `scan(tl, sel, at, {duration, color, fromColor, stagger})` | soldan sağa fosforlu kalem · `BK.scan(tl, "#x-hl", 1.6)` |
| `burst(tl, ".bk-burst", at, {sparks})` | çizgiler dışa çizilir + parıltılar pop; `.bk-burst` `data-rays data-r data-from data-to` |
| `note(tl, ".bk-note", at)` | not belirir (kısa kayma); `.bk-note` ya da `.bk-note--plain` |
| `mascotIn(tl, box, at, {from:"right"|"left"|"bottom", rotation})` | kayar + kısa inişle oturur (0.7 sn) |
| `mascotReact(tl, box, at, {kind:"hop"|"shake"|"tilt"|"squash", angle})` | tek kısa tepki (≤ 0.4 sn, küçük genlik) |
| `mascotSwap(tl, box, fromImg, toImg, at)` | poz değişir + sıçrama · `BK.mascotSwap(tl, "#x-m", "#x-pose-a", "#x-pose-b", 7.2)` |
| `type(tl, el, at, {cps, caret, caretAt, hold})` → bitiş | harf harf yazar (display). İmleç yalnız `caret` verilirse yönetilir: `caret:"#x-caret"` (metin span'inin ardındaki `.bk-caret`), `caretAt` (vars. at) görünür, bitişten `hold` sn (vars. .15) sonra söner · `var e = BK.type(tl, "#x-you", 1.45, {cps:22, caret:"#x-caret"})` |
| `stream(tl, el, at, {wps})` → bitiş | cevap kelime kelime akar · `e = BK.stream(tl, "#x-bot", e + .2, {wps:14})` |
| `termMeta(tl, [meta, en], at)` | meta + EN satırı en son yükselir |
| `termMark(tl, mark, note, at, {color})` | terminal metnine şerit (yazı mürekkebe döner) + yanında not (terminalde `.bk-note--plain --on-dark`) |
| `bars(tl, ".bk-bar-fill", at, {stagger})` | çubuklar soldan büyür (taşar, oturur) |
| `check(tl, row, at, {rotation, noStamp})` | satır + tik + damga |
| `string(tl, "path", at, {pins, stagger})` | SVG ip çizilir, raptiyeler pop |
| `formula(tl, parts, at, {stagger})` | parçalar sırayla pop |
| `rest(i)` `stepAt(i)` `plan([d1,d2,..])` | eşit/değişken zaman planı · `BK.plan([1.1, 3.3])` → `{rest, at, fragments}` |

Tutarlılık: panel/kart → slam · damga → stamp · sayı → count · vurgu → scan · maskot → mascotIn/React/Swap · terminal → type/stream/termMeta/termMark.
Canlı köprü: canlı modda (slideshow içinde) `gsap.ticker.lagSmoothing(0)` açılır; rAF kısılsa da (arka plan sekmesi) geçiş duvar saatine göre biter.

## 5. Zaman kuralı (yerel saat)
- Giriş 0 → ≤ 1.2; ilk bekleme 1.4. Varsayılan adım: hareket `rest(i-1)+0.05`, ≤ 0.9 sn, bekleme `rest(i)=1.4+1.1·i`.
- Demo/çok adımlı sahne değişken adım kullanır (demo-memory: `1.4, 4.7, 8, 9.1, 10`; window 11). Her bekleme karesinden 0.1 sn önce her şey durmuş olmalı.
- Her fragment adımında ≥ 2 öğe hareket eder (içerik + maskot tepkisi ya da süs).
- Navigasyon SEEK eder: ileri/geri doğrudan atlamada kare eksiksiz (kontrol edildi: demo-memory 66 → 57.4 → 64 → 60.7).

## 6. Zaman planı (birlestir.mjs çıktısı; window değişirse kayar)
**Açık karar (şef):** icerik.md tokens sahnesini ikiye böldü (12a `tokens`, 12b `tokens-output`). deck.json hâlâ 22 slayt. Bölünürse slayt ajanları başlamadan: deck.json'a `tokens-output` ekle, `node atolye/birlestir.mjs`, bu tabloyu ve 6 referans sahnedeki `NN / 22` numaralarını güncelle. Numaralar sahnelerde elle yazılı (`.bk-no`).
| # | sceneId | başlangıç | win | W1.x / folio | maskot |
|---|---|---|---|---|---|
| 1 | cover | 0 | 8 | AIC390 / WEEK 01 | selam |
| 2 | roadmap | 8 | 8 | BELDESK / MAP · repo linki | gorevli |
| 3 | team-agreement | 16 | 8 | W1.1 · docs/team_agreement.md | selam |
| 4 | customer | 24 | 8 | W1.2 · docs/use_case_brief.md | isaret |
| 5 | stories-scope | 32 | 8 | W1.2 · docs/use_case_brief.md | gorevli |
| 6 | test-set | 40 | 8 | W1.3 · docs/test_set_week1.md | buyutec |
| 7 | data-inventory | 48 | 8 | W1.4 · docs/data_inventory.md | buyutec |
| 8 | demo-memory | 56 | 11 | Live demo · scripts/try_chat.py | yaziyor → unutkan |
| 9 | demo-pothole | 67 | 8 | Live demo · scripts/try_chat.py | yaziyor → mahcup |
| 10 | baseline-call | 75 | 8 | W1.5 · eval/results/week1/ | isaret |
| 11 | temperature | 83 | 8 | W1.5 · docs/baseline_analysis_week1.md | dusunen |
| 12 | tokens | 91 | 8 | W1.5 (+W1.6) · eval/results/week1/ | buyutec |
| 13 | cost | 99 | 8 | W1.6 · scripts/cost_estimate.py | gorevli |
| 14 | failure-injection | 107 | 8 | W1.5 gözlem | saskin |
| 15 | failure-tools | 115 | 8 | W1.5 gözlem | mahcup |
| 16 | failure-facts | 123 | 8 | W1.5 gözlem | unutkan |
| 17 | predicted-failures | 131 | 8 | W1.7 · docs/predicted_failures.md | dusunen |
| 18 | repository | 139 | 8 | W1.8 · README.md (`week-1` etiketi YOK → "tag pending") | gorevli |
| 19 | scoreboard-measured | 147 | 8 | BELDESK / SCOREBOARD · reports/week-1.md | isaret |
| 20 | scoreboard-null | 155 | 8 | BELDESK / SCOREBOARD · reports/week-1.md | dusunen |
| 21 | next-week | 163 | 8 | BELDESK / NEXT WEEK | gorevli |
| 22 | questions | 171 | 8 | BELDESK / QUESTIONS (3 hotspot) | yaziyor |
| dal | q-measurement · q-failure · q-priority | 179 · 187 · 195 | 8 | BELDESK / QUESTIONS | buyutec · dusunen · gorevli |
Repo yolları `deck.json` `repo` alanında; doğrusu `icerik.md` ise onu kullan ve şefe bildir.

## 7. Doğrulama (tek sırada!)
```bash
cd /Users/efeincirci/Desktop/Dersler/AIC390/Project/deck/week1
node atolye/birlestir.mjs                                   # sahne ekleyince/window değişince
atolye/sira.sh snapshot --at <başlangıç+her bekleme>,<bir ara kare> --no-end --output <scratchpad>/<id>
atolye/sira.sh check --json > <scratchpad>/<id>-check.json  # layout/contrast/runtime errorCount 0
```
Her PNG'yi Read ile AÇ: taşma, binme, font, ğ ş ı İ, maskot yazıyı örtüyor mu, "gururla gösterir miydim?".
Beklenen uyarılar: `film_silent`, `audio_none`, `first_frame_empty` (kapakta 0. kare boş kağıt), `composition_file_too_large`,
demo sahnelerinde `line_unread` (canlıda sunucu bekletir). Başka her bulgu düzeltilir.
Canlı: `hyperframes present composition --no-open --port <boş>` (birleştirici sonrası yeniden başlat).
