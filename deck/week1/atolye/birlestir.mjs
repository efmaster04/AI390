#!/usr/bin/env node
// Birleştirici: atolye/deck.json + composition/scenes/<sceneId>.html -> composition/index.html ve kök index.html.
// Kullanım:  node atolye/birlestir.mjs            (index dosyalarını yeniden yazar)
//            node atolye/birlestir.mjs --stubs    (eksik sahne dosyaları için yer tutucu da yazar)
// Sahne dosyalarına DOKUNMAZ (yalnız --stubs ile, olmayan dosyayı oluşturur).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const week = join(here, "..");
const comp = join(week, "composition");
const deck = JSON.parse(readFileSync(join(here, "deck.json"), "utf8"));
const W = deck.window;
const makeStubs = process.argv.includes("--stubs");

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const r3 = (n) => Math.round(n * 1000) / 1000;

// Sahne sırası: ana slaytlar, sonra dal slaytları. Pencere: sahne kökündeki data-window (yoksa deck.window).
const order = [
  ...deck.slides.map((s) => ({ ...s, branch: null })),
  ...deck.slideSequences.flatMap((q) => q.slides.map((s) => ({ ...s, branch: q.id }))),
];
const sceneFile = (s) => join(comp, "scenes", `${s.sceneId}.html`);
let cursor = 0;
for (const s of order) {
  if (makeStubs && !existsSync(sceneFile(s))) writeFileSync(sceneFile(s), stub(s));
  const html = existsSync(sceneFile(s)) ? readFileSync(sceneFile(s), "utf8") : "";
  const m = /data-window="([^"]*)"/.exec(html);
  s.win = m ? Number(m[1]) : W;
  s.start = r3(cursor);
  cursor += s.win;
}
const total = r3(cursor);

const errors = [];
function fragmentsOf(s) {
  const file = sceneFile(s);
  if (!existsSync(file)) errors.push(`eksik sahne dosyası: scenes/${s.sceneId}.html`);
  const html = existsSync(file) ? readFileSync(file, "utf8") : "";
  const m = /data-fragments="([^"]*)"/.exec(html);
  const local = (m ? m[1] : "1.4").split(",").map((x) => Number(x.trim())).filter((x) => !Number.isNaN(x));
  local.forEach((t, i) => {
    if (!(t > 0 && t < s.win - 0.3)) errors.push(`${s.sceneId}: fragment ${t} pencere dışında (0, ${s.win - 0.3})`);
    if (i > 0 && t <= local[i - 1]) errors.push(`${s.sceneId}: fragment'lar artan sırada olmalı`);
  });
  return local.map((t) => r3(s.start + t));
}

function slideJson(s) {
  const o = { sceneId: s.sceneId, notes: s.notes, fragments: fragmentsOf(s) };
  if (s.hotspots) o.hotspots = s.hotspots;
  return o;
}
const island = {
  slides: deck.slides.map((s) => slideJson(order.find((o) => o.sceneId === s.sceneId))),
  slideSequences: deck.slideSequences.map((q) => ({
    id: q.id, label: q.label,
    slides: q.slides.map((s) => slideJson(order.find((o) => o.sceneId === s.sceneId))),
  })),
};
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
const islandText = JSON.stringify(island, null, 2).replace(/</g, "\\u003c");
const indent = (txt, n) => txt.split("\n").map((l) => " ".repeat(n) + l).join("\n");

const hosts = order.map((s, i) => `      <div id="${s.sceneId}" data-composition-id="${s.sceneId}" data-composition-src="scenes/${s.sceneId}.html"
        data-label="${esc(s.no + " " + s.title)}" data-start="${s.start}" data-duration="${s.win}" data-track-index="${i}"
        data-track-kind="graphics" data-width="${deck.width}" data-height="${deck.height}"></div>`).join("\n");

const composition = `<!doctype html>
<!-- ÜRETİLMİŞ DOSYA: elle düzenleme. Kaynak: atolye/deck.json + scenes/*.html -> node atolye/birlestir.mjs -->
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Beldesk Week 1</title>
    <link rel="stylesheet" href="assets/kit/kit.css" />
    <script src="assets/kit/gsap.min.js"></script>
    <script src="assets/kit/kit.js"></script>
    <style>
      html, body { margin: 0; width: ${deck.width}px; height: ${deck.height}px; overflow: hidden; background: #e8c58f; }
    </style>
  </head>
  <body>
    <script type="application/hyperframes-slideshow+json">
${indent(islandText, 6)}
    </script>
    <div id="main" data-composition-id="main" data-start="0" data-duration="${total}" data-width="${deck.width}" data-height="${deck.height}">
${hosts}
    </div>
    <script>
      // Kök timeline yalnız toplam süreyi taşır; sahneler kendi timeline'larını kaydeder (kit.js / BK.scene).
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = gsap.timeline({ paused: true }).set({}, {}, ${total});
    </script>
  </body>
</html>
`;
writeFileSync(join(comp, "index.html"), composition);

const wrapper = `<!doctype html>
<!-- ÜRETİLMİŞ DOSYA: canlı deck kabı. Bir HTTP sunucusundan açılır (ör. hyperframes present composition). -->
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Beldesk Week 1 — Deck</title>
    <script src="vendor/hyperframes-player.global.js"></script>
    <script src="vendor/hyperframes-slideshow.global.js"></script>
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      html, body { width: 100%; height: 100%; overflow: hidden; background: #e8c58f; }
    </style>
  </head>
  <body>
    <hyperframes-slideshow tabindex="0" notes-storage-key="beldesk-week1" style="display: block; position: relative; width: 100vw; height: 100vh">
      <hyperframes-player interactive runtime-src="vendor/hyperframe.runtime.iife.js" style="position: absolute; inset: 0" src="composition/index.html"></hyperframes-player>
      <!-- composition/index.html içindeki adanın kopyası (birlestir.mjs ikisini birlikte yazar) -->
      <script type="application/hyperframes-slideshow+json">
${indent(islandText, 8)}
      </script>
    </hyperframes-slideshow>
  </body>
</html>
`;
writeFileSync(join(week, "index.html"), wrapper);
console.log(`ok: ${order.length} sahne, toplam ${total} sn`);
order.forEach((s) => console.log(`  ${String(s.start).padStart(6)}–${String(r3(s.start + s.win)).padEnd(6)} ${s.sceneId}${s.branch ? "  (dal: " + s.branch + ")" : ""}`));

function stub(s) {
  const id = s.sceneId;
  const tab = s.tag
    ? `<span class="bk-deliv"><span class="bk-deliv-id">${esc(s.tag)}</span>${esc(s.tagName || "")}</span>`
    : `<span class="bk-folio">${esc(s.folio)}</span>`;
  const repo = s.repo ? `\n      <div class="bk-repo"><span class="bk-repo-k">repo</span>${esc(s.repo)}</div>` : "";
  const pose = s.mascot || "gorevli";
  return `<template id="${id}-template">
  <style>
    #root { position: absolute; inset: 0; }
    [data-composition-id="${id}"] #${id}-mascot { right: 120px; bottom: 60px; }
    [data-composition-id="${id}"] .bk-body { top: 400px; }
  </style>
  <div id="root" data-composition-id="${id}" data-hold data-width="1920" data-height="1080" data-window="8" data-fragments="1.4">
    <div class="bk-stage">
      <div class="bk-sheet"></div>
      <header class="bk-band">${tab}<span class="bk-section">${esc(s.section)}</span><span class="bk-no">${esc(s.no)}</span></header>
      <div class="bk-rule"></div>
      <h2 class="bk-title">${esc(s.title)}</h2>
      <div class="bk-body"><p class="bk-label">STUB / ${esc(id)}</p></div>${repo}
      <div id="${id}-mascot" class="bk-mascot bk-mascot--aide bk-mascot--${pose}"><img class="bk-mascot-pose" src="assets/maskot/${pose}.png" alt=""></div>
    </div>
  </div>
  <script>
    BK.scene("${id}", function (tl, root, BK) {
      BK.frame(tl, root, 0);
      BK.mascotIn(tl, "#${id}-mascot", 0.3);
    });
  </script>
</template>
`;
}
