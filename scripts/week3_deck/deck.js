/* Week 3 "journey of one question" helpers (window.W3). Built on the Week 2 kit (window.BK).
   Rules: every tween is a fromTo on the scene timeline; no timers, no randomness, no onUpdate DOM writes.
   Geometry is measured once at scene setup (after fonts), before any tween touches the measured elements. */
(function () {
  "use strict";
  function q(root, sel) { return typeof sel === "string" ? root.querySelectorAll(sel) : sel; }
  function one(root, sel) { return typeof sel === "string" ? root.querySelector(sel) : sel; }
  // Position of el inside the .bk-stage, from the offset chain (ignores CSS transforms and player scaling).
  function pos(el, stage) {
    var x = 0, y = 0, n = el;
    while (n && n !== stage) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return { x: x, y: y, w: el.offsetWidth, h: el.offsetHeight };
  }
  // Rail: line draws, stations pop, the question bubble travels from the previous station to this one.
  function rail(tl, root, at) {
    var r = root.querySelector(".w3-rail");
    if (!r) return;
    BK.draw(tl, r.querySelector(".w3-rail-line"), at, { duration: 0.45 });
    tl.fromTo(r.querySelectorAll(".w3-st"), { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.25, stagger: 0.04, ease: BK.EASE.pop }, at + 0.05);
    var done = r.querySelector(".w3-rail-done");
    if (done) BK.draw(tl, done, at + 0.25, { duration: 0.45 });
    var bub = r.querySelector(".w3-rail-bub");
    if (bub) {
      var dx = parseFloat(bub.getAttribute("data-from") || "0");
      tl.fromTo(bub, { x: dx, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6, ease: BK.EASE.move }, at + 0.3);
    }
  }
  // Move the rail bubble later in the scene (second tween on x: immediateRender false).
  function railStep(tl, root, dx, at, from, to) {
    var r = root.querySelector(".w3-rail");
    var bub = r.querySelector(".w3-rail-bub");
    tl.fromTo(bub, { x: 0 }, { x: dx, duration: 0.55, ease: BK.EASE.move, immediateRender: false }, at);
    if (from == null || to == null) return;
    // The station it leaves turns "done" (teal), the one it reaches turns "now" (sun); the done track grows with it.
    var st = r.querySelectorAll(".w3-st");
    tl.fromTo(st[from].querySelectorAll("b, i"), { backgroundColor: "#fec835" }, { backgroundColor: "#38ac9d", duration: 0.25, immediateRender: false }, at + 0.1);
    tl.fromTo(st[to].querySelectorAll("b, i"), { backgroundColor: "#fff6e0" }, { backgroundColor: "#fec835", duration: 0.25, immediateRender: false }, at + 0.4);
    tl.fromTo(st[from].querySelector("span"), { color: "#161310" }, { color: "#4a3f33", duration: 0.25, immediateRender: false }, at + 0.1);
    tl.fromTo(st[to].querySelector("span"), { color: "#4a3f33" }, { color: "#161310", duration: 0.25, immediateRender: false }, at + 0.4);
    var done = r.querySelector(".w3-rail-done");
    if (done) { var w = done.offsetWidth; tl.fromTo(done, { width: w }, { width: w + dx, duration: 0.55, ease: BK.EASE.move, immediateRender: false }, at); }
  }
  // Curve from the right edge of a to the left edge of b (or to its right edge when b sits left of a).
  function linkPath(stage, a, b) {
    var p = pos(a, stage), t = pos(b, stage);
    var x1 = p.x + p.w + 6, y1 = p.y + p.h / 2, x2, y2 = t.y + t.h / 2;
    if (t.x > x1) { x2 = t.x - 8; } else { x1 = p.x - 6; x2 = t.x + t.w + 8; }
    var mx = (x1 + x2) / 2;
    return "M" + x1.toFixed(1) + " " + y1.toFixed(1) + " C" + mx.toFixed(1) + " " + y1.toFixed(1) + " " + mx.toFixed(1) + " " + y2.toFixed(1) + " " + x2.toFixed(1) + " " + y2.toFixed(1);
  }
  // Measure all [data-link-from]/[data-link-to] pairs into their SVG paths. Call before tweens.
  function measureLinks(root) {
    var stage = root.querySelector(".bk-stage");
    Array.prototype.forEach.call(root.querySelectorAll("path[data-link-from]"), function (p) {
      var a = root.querySelector(p.getAttribute("data-link-from")), b = root.querySelector(p.getAttribute("data-link-to"));
      var card = b && b.closest(".w3-src");
      if (a && b && card) {
        var s0 = pos(a, stage), c = pos(card, stage), t0 = pos(b, stage);
        // Leave the chip horizontally (nothing follows a chip on its line), then curve to the quote's first line.
        var term = a.closest(".bk-term"), tx = term ? pos(term, stage).x + pos(term, stage).w + 4 : s0.x + s0.w + 30;
        var x1 = s0.x + s0.w + 6, y1 = s0.y + s0.h / 2, x2 = c.x - 8, y2 = t0.y + 18, mx = (tx + x2) / 2;
        p.setAttribute("d", "M" + x1 + " " + y1 + " L" + tx + " " + y1 + " C" + mx + " " + y1 + " " + mx + " " + y2 + " " + x2 + " " + y2);
      } else if (a && b) p.setAttribute("d", linkPath(stage, a, b));
      var dot = root.querySelector(p.getAttribute("data-link-dot") || "#none");
      if (dot && b) {
        var t = pos(b, stage), s = pos(a, stage);
        var x = t.x > s.x + s.w ? t.x - 8 : t.x + t.w + 8;
        dot.style.left = (x - 9) + "px"; dot.style.top = (t.y + t.h / 2 - 9) + "px";
      }
    });
  }
  // Number flip: old value slides up and fades, new value rises in (both spans stacked in one .w3-flip box).
  function flip(tl, oldEl, newEl, at) {
    tl.fromTo(oldEl, { opacity: 1, y: 0 }, { opacity: 0, y: -26, duration: 0.3, ease: BK.EASE.settle, immediateRender: false }, at);
    tl.fromTo(newEl, { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.35, ease: BK.EASE.settle }, at + 0.08);
  }
  // Bar morph: scaleX from one fraction to another (both relative to the full track).
  function morph(tl, el, from, to, at, first) {
    tl.fromTo(el, { scaleX: from, transformOrigin: "0% 50%" }, { scaleX: to, duration: 0.6, ease: BK.EASE.settle, immediateRender: !!first }, at);
  }
  // Ranked cards: entry from the side, later reorder by a y offset (px) computed at build time.
  function reorder(tl, root, at) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-dy]"), function (c) {
      var dy = parseFloat(c.getAttribute("data-dy"));
      tl.fromTo(c, { y: dy }, { y: 0, duration: dy ? 0.8 : 0.01, ease: "power2.inOut" }, at + (Math.abs(dy) > 200 ? 0 : 0.12));
    });
  }
  window.W3 = { pos: pos, rail: rail, railStep: railStep, measureLinks: measureLinks, flip: flip, morph: morph, reorder: reorder, q: q, one: one };
})();
