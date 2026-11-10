/* Beldesk Week 1 — ortak GSAP kiti v3 (window.BK). Sahne ajanları bu dosyayı DEĞİŞTİRMEZ.
   Kural: her şey timeline zamanının fonksiyonu (seek ile doğru kare). Zamanlayıcı, Date.now, rastgelelik, döngü yok.
   Her yardımcı (tl, hedef, at, o) imzalı ve fromTo kullanır; aynı öğe+özelliğe ikinci tween'de immediateRender:false. */
(function () {
  "use strict";

  // ---- Zaman sabitleri (saniye, sahnenin yerel saati) ----
  var T = {
    WINDOW: 8,      // varsayılan pencere; sahne kökünde data-window ile değişir
    ENTER: 1.2,     // giriş en geç bu anda biter
    REST0: 1.4,     // ilk durağan kare
    STEP: 1.1,      // varsayılan fragment aralığı
    LEAD: 0.05,     // adım hareketi, önceki bekleme karesinden bu kadar sonra başlar
    MOVE: 0.9       // bir adımın hareket süresi üst sınırı (demo yazımı hariç)
  };
  function r3(n) { return Math.round(n * 1000) / 1000; }
  // i. durağan karenin yerel zamanı (varsayılan eşit aralık)
  function rest(i) { return r3(T.REST0 + i * T.STEP); }
  // i. adımın (i >= 1) başladığı yerel zaman
  function stepAt(i) { return r3(rest(i - 1) + T.LEAD); }
  // Değişken aralık: BK.plan([1.1, 4.2, 1.1]) -> {rest:[1.4,2.5,6.7,7.8], at:[_,1.45,2.55,6.75], fragments:"1.4,2.5,6.7,7.8"}
  function plan(steps) {
    var rs = [T.REST0], at = [null];
    steps.forEach(function (d) { at.push(r3(rs[rs.length - 1] + T.LEAD)); rs.push(r3(rs[rs.length - 1] + d)); });
    return { rest: rs, at: at, fragments: rs.join(",") };
  }

  // ---- Easing: canlı ama "kendinden emin" (ton ayarı): taşma küçük, lastik/elastik/sekme yok, hızlı oturur ----
  var EASE = {
    enter: "expo.out", settle: "power3.out", move: "power2.inOut", draw: "power1.inOut", count: "power2.out", exit: "power3.in",
    slam: "back.out(1.15)",  // kağıt iner, çok az taşar, oturur
    pop: "back.out(1.5)",    // süs / damga sonrası
    land: "back.out(1.2)"    // maskot iniş (sekme yok)
  };
  var DUR = { word: 0.22, words: 0.06, rise: 0.55, stagger: 0.08, slam: 0.5, draw: 0.5, scan: 0.5, stamp: 0.3, count: 0.85, dim: 0.35, travel: 0.7 };

  function q(sel, root) {
    if (typeof sel !== "string") return sel;
    return (root || document).querySelectorAll(sel);
  }
  function one(sel) { var n = q(sel); return n && n.length !== undefined && !n.nodeType ? n[0] : n; }

  // Metni kelime span'lerine böler (kurulumda bir kez).
  function words(el) {
    el = one(el);
    if (!el || el.getAttribute("data-bk-split") === "1") return el ? el.querySelectorAll(".bk-word") : [];
    var walk = function (node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(function (p) {
            if (!p) return;
            if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(p)); return; }
            var s = document.createElement("span"); s.className = "bk-word"; s.textContent = p; frag.appendChild(s);
          });
          node.replaceChild(frag, n);
        } else if (n.nodeType === 1 && !n.classList.contains("bk-word") && !n.classList.contains("bk-caret")) walk(n);
      });
    };
    walk(el);
    el.setAttribute("data-bk-split", "1");
    return el.querySelectorAll(".bk-word");
  }
  // Metni harf span'lerine böler (BK.type için).
  function chars(el) {
    el = one(el);
    if (!el || el.getAttribute("data-bk-chars") === "1") return el ? el.querySelectorAll(".bk-char") : [];
    var walk = function (node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = document.createDocumentFragment();
          Array.from(n.textContent).forEach(function (c) {
            var s = document.createElement("span"); s.className = "bk-char"; s.textContent = c; frag.appendChild(s);
          });
          node.replaceChild(frag, n);
        } else if (n.nodeType === 1 && !n.classList.contains("bk-caret")) walk(n);
      });
    };
    walk(el);
    el.setAttribute("data-bk-chars", "1");
    return el.querySelectorAll(".bk-char");
  }

  // ================= Temel giriş yardımcıları =================
  function titleIn(tl, el, at) {
    var w = words(el);
    tl.fromTo(w, { opacity: 0, y: 18 },
      { opacity: 1, y: 0, duration: 0.38, stagger: DUR.words * 0.7, ease: EASE.settle }, at);
    return tl;
  }
  function rise(tl, targets, at, o) {
    o = o || {};
    tl.fromTo(q(targets), { opacity: 0, y: o.y == null ? 24 : o.y },
      { opacity: 1, y: 0, duration: o.duration || DUR.rise, stagger: o.stagger == null ? DUR.stagger : o.stagger, ease: EASE.enter, immediateRender: !o.later }, at);
    return tl;
  }
  function fade(tl, targets, at, o) {
    o = o || {};
    tl.fromTo(q(targets), { opacity: o.from == null ? 0 : o.from },
      { opacity: o.to == null ? 1 : o.to, duration: o.duration || DUR.dim, stagger: o.stagger || 0, ease: EASE.settle, immediateRender: !o.later }, at);
    return tl;
  }
  // Kağıt gibi oturma: yukarıdan kısa iner, çok az büyük gelir, hafif taşar ve yerine oturur. Son eğim vars. 0 (ton ayarı).
  function slam(tl, targets, at, o) {
    o = o || {};
    var rot = o.rotation == null ? 0 : o.rotation;
    tl.fromTo(q(targets), { opacity: 0, y: o.y == null ? -28 : o.y, scale: 1.03, rotation: rot + (o.spin == null ? -1.5 : o.spin) },
      { opacity: 1, y: 0, scale: 1, rotation: rot, duration: o.duration || DUR.slam, stagger: o.stagger == null ? 0.1 : o.stagger, ease: EASE.slam, immediateRender: !o.later }, at);
    return tl;
  }
  // v1 adı korunur: panelIn artık slam (clip-path ofset gölgeyi kesiyordu).
  function panelIn(tl, targets, at, o) { return slam(tl, targets, at, o); }
  // Çizgi çizer (scaleX 0 -> 1, sol kökenli). Dikey: o.axis = "y".
  function draw(tl, el, at, o) {
    o = o || {};
    var y = o.axis === "y";
    var from = y ? { scaleY: 0, transformOrigin: "50% 0%" } : { scaleX: 0, transformOrigin: "0% 50%" };
    var to = y ? { scaleY: 1 } : { scaleX: 1 };
    to.duration = o.duration || DUR.draw; to.ease = EASE.draw; to.stagger = o.stagger || 0;
    tl.fromTo(q(el), from, to, at);
    return tl;
  }
  // Fosforlu kalem: .bk-scan şeridi soldan sağa; o.color verilirse yazı rengi döner (koyu zeminde mürekkebe).
  function scan(tl, el, at, o) {
    o = o || {};
    tl.fromTo(q(el), { backgroundSize: "0% 100%" },
      { backgroundSize: "100% 100%", duration: o.duration || DUR.scan, stagger: o.stagger || 0, ease: EASE.draw }, at);
    if (o.color) tl.fromTo(q(el), { color: o.fromColor || "#fff1d6" }, { color: o.color, duration: (o.duration || DUR.scan) * 0.6, stagger: o.stagger || 0, ease: EASE.draw }, at + (o.duration || DUR.scan) * 0.3);
    return tl;
  }
  // Damga vurma: büyükten sert iner (0.18 sn), sonra tek kısa geri tepme. Toplam ~0.4 sn. Eğim vars. -3 (ton: en fazla ±3°).
  function stamp(tl, el, at, o) {
    o = o || {};
    var rot = o.rotation == null ? -3 : o.rotation;
    var n = q(el), st = o.stagger || 0;
    tl.fromTo(n, { opacity: 0, scale: 1.5, rotation: rot - 4 },
      { opacity: 1, scale: 1, rotation: rot, duration: 0.18, stagger: st, ease: "power4.in" }, at);
    tl.fromTo(n, { x: -4 }, { x: 0, duration: 0.2, stagger: st, ease: EASE.settle, immediateRender: false }, at + 0.18);
    if (o.shake) tl.fromTo(q(o.shake), { y: 3 }, { y: 0, duration: 0.2, ease: EASE.settle, immediateRender: false }, at + 0.18);
    return tl;
  }
  // Sayı sayma (innerText tween'i, geri çağrı yok: runtime suppressEvents ile seek eder). Öğe YALNIZ rakamı tutar;
  // "$", "/75", "%" gibi ekler ayrı span'de. o.decimals: ondalık adım (snap 10^-d; sondaki sıfırlar düşebilir, son değer
  // sayının kendisi olarak yazılır: tam ondalık gösterim gerekiyorsa o.decimals verme, sayıyı sabit yaz ve BK.slam kullan).
  function count(tl, el, to, at, o) {
    o = o || {};
    var snap = o.decimals ? Math.pow(10, -o.decimals) : 1;
    tl.fromTo(q(el), { innerText: o.from || 0 }, { innerText: to, snap: { innerText: snap }, duration: o.duration || DUR.count, ease: EASE.count }, at);
    return tl;
  }
  function travel(tl, el, at, from, to, o) {
    o = o || {};
    var t = { duration: o.duration || DUR.travel, ease: EASE.move, immediateRender: !o.later };
    for (var k in to) t[k] = to[k];
    tl.fromTo(q(el), from, t, at);
    return tl;
  }
  function dim(tl, targets, at, o) {
    o = o || {};
    tl.fromTo(q(targets), { opacity: o.from == null ? 1 : o.from }, { opacity: o.to == null ? 0.35 : o.to, duration: DUR.dim, ease: EASE.settle, immediateRender: false }, at);
    return tl;
  }
  // Süs patlaması: .bk-burst çizgileri dışa çizilir + .bk-spark'lar pop eder; sonra DURUR.
  function burst(tl, el, at, o) {
    o = o || {};
    var nodes = q(el);
    Array.prototype.forEach.call(nodes, function (b) {
      var rays = b.querySelectorAll("i");
      tl.fromTo(rays, { scaleX: 0, opacity: 1 }, { scaleX: 1, duration: 0.3, stagger: 0.03, ease: EASE.settle }, at);
    });
    if (o.sparks) tl.fromTo(q(o.sparks), { scale: 0, rotation: -30, opacity: 0 }, { scale: 1, rotation: 0, opacity: 1, duration: 0.32, stagger: 0.05, ease: EASE.pop }, at + 0.05);
    return tl;
  }
  // Burst çizgilerini kurulumda yerleştirir: <div class="bk-burst" data-rays="7" data-r="40" data-from="-150" data-to="-30">
  function layoutBursts(root) {
    Array.prototype.forEach.call(root.querySelectorAll(".bk-burst"), function (b) {
      if (b.children.length) return;
      var n = +b.getAttribute("data-rays") || 6, r = +b.getAttribute("data-r") || 36;
      var a0 = +(b.getAttribute("data-from") || -160), a1 = +(b.getAttribute("data-to") || -20);
      for (var i = 0; i < n; i++) {
        var a = n === 1 ? a0 : a0 + (a1 - a0) * i / (n - 1), rad = a * Math.PI / 180;
        var ray = document.createElement("i");
        ray.style.left = (Math.cos(rad) * r) + "px"; ray.style.top = (Math.sin(rad) * r) + "px";
        ray.style.rotate = a + "deg";
        b.appendChild(ray);
      }
    });
  }

  // ================= Maskot =================
  // Giriş: yandan kayar, kısa bir inişle oturur (≤ 0.75 sn), sonra durur. o.from: "right" | "left" | "bottom"; o.rotation son eğim.
  function mascotIn(tl, el, at, o) {
    o = o || {};
    var dx = o.from === "left" ? -160 : o.from === "bottom" ? 0 : 160;
    var n = q(el);
    tl.fromTo(n, { opacity: 0, x: dx, rotation: dx ? (dx > 0 ? 4 : -4) : 0 },
      { opacity: 1, x: 0, rotation: o.rotation || 0, duration: 0.5, ease: EASE.settle }, at);
    tl.fromTo(n, { y: o.from === "bottom" ? 180 : -50 }, { y: 0, duration: 0.7, ease: EASE.land }, at);
    return tl;
  }
  // Tepki: tek kısa hareket. kind: "hop" (sıçrama) | "shake" (sarsılma) | "tilt" (eğilme) | "squash" (şaşırma).
  function mascotReact(tl, el, at, o) {
    o = o || {};
    var n = q(el), k = o.kind || "hop", base = o.rotation || 0;
    // Ton ayarı: küçük genlik, elastik/sekme yok; her tepki ≤ 0.4 sn'de durur.
    if (k === "hop") {
      tl.fromTo(n, { y: 0 }, { y: -20, duration: 0.14, ease: "power2.out", immediateRender: false }, at);
      tl.fromTo(n, { y: -20 }, { y: 0, duration: 0.24, ease: EASE.settle, immediateRender: false }, at + 0.14);
    } else if (k === "shake") {
      tl.fromTo(n, { rotation: base - 3 }, { rotation: base, duration: 0.35, ease: "back.out(2)", immediateRender: false }, at);
    } else if (k === "tilt") {
      tl.fromTo(n, { rotation: base }, { rotation: base + (o.angle || -4), duration: 0.35, ease: EASE.slam, immediateRender: false }, at);
    } else if (k === "squash") {
      tl.fromTo(n, { scaleY: 0.95, scaleX: 1.02, transformOrigin: "50% 100%" }, { scaleY: 1, scaleX: 1, duration: 0.3, ease: EASE.settle, immediateRender: false }, at);
    }
    return tl;
  }
  // Poz değiştirme: kutudaki eski poz söner, yenisi pop eder, kutu küçük sıçrar. fromImg/toImg: .bk-mascot-pose öğeleri.
  // Kural: kutudaki 2. ve sonraki pozlar ilk swap'ına kadar gizli kalır (bu çağrı kurulumda gizler).
  function mascotSwap(tl, box, fromImg, toImg, at) {
    tl.fromTo(q(toImg), { opacity: 0, scale: 0.95, transformOrigin: "50% 100%" }, { opacity: 1, scale: 1, duration: 0.4, ease: EASE.pop }, at + 0.08);
    tl.fromTo(q(fromImg), { opacity: 1 }, { opacity: 0, duration: 0.12, ease: "none", immediateRender: false }, at + 0.06);
    mascotReact(tl, box, at, { kind: "hop" });
    return tl;
  }

  // ================= Terminal =================
  // Karakter karakter yazma (you> satırı). el: yazılacak metni tutan span (prompt dışında). o.cps harf/sn (vars. 26).
  // İmleç YALNIZ o.caret verilirse yönetilir (seçici, ör. "#x-caret": el'in ardına konan .bk-caret span'i).
  // İmleç o.caretAt anından (vars. at) görünür, yazım bitince o.hold sn (vars. 0.15) sonra söner. Dönüş: bitiş zamanı.
  function type(tl, el, at, o) {
    o = o || {};
    var cs = chars(el), cps = o.cps || 26, gap = 1 / cps;
    tl.fromTo(cs, { display: "none" }, { display: "inline", duration: 0.001, stagger: gap, ease: "none" }, at);
    var end = r3(at + cs.length * gap);
    var caret = o.caret ? one(o.caret) : null;
    if (caret) {
      var on = o.caretAt == null ? at - 0.001 : o.caretAt;
      tl.fromTo(caret, { opacity: 0 }, { opacity: 1, duration: 0.001 }, on);
      tl.fromTo(caret, { opacity: 1 }, { opacity: 0, duration: 0.001, immediateRender: false }, end + (o.hold == null ? 0.15 : o.hold));
    }
    return end;
  }
  // Cevap akışı (beldesk>): kelime kelime belirir. o.wps kelime/sn (vars. 16). Dönüş: bitiş zamanı.
  function stream(tl, el, at, o) {
    o = o || {};
    var ws = words(el), wps = o.wps || 16, gap = 1 / wps;
    tl.fromTo(ws, { opacity: 0 }, { opacity: 1, duration: 0.08, stagger: gap, ease: "none" }, at);
    return r3(at + ws.length * gap + 0.08);
  }
  // Meta satırı ([tokens …]) ve EN çeviri satırı: en son, yükselerek.
  function termMeta(tl, el, at) { return rise(tl, el, at, { y: 10, duration: 0.35, stagger: 0.12 }); }
  // Terminal metninin bir parçasına şerit + yanında el yazısı not. mark: .bk-scan span; note: .bk-note öğesi.
  function termMark(tl, mark, note, at, o) {
    o = o || {};
    scan(tl, mark, at, { duration: o.duration || 0.45, color: o.color === undefined ? "#161310" : o.color, fromColor: o.fromColor });
    if (note) tl.fromTo(q(note), { opacity: 0, scale: 0.9, x: -10 }, { opacity: 1, scale: 1, x: 0, duration: 0.3, ease: EASE.settle }, at + 0.3);
    return tl;
  }
  // Not tek başına (terminal dışı): .bk-note (el yazısı, slaytta en fazla 1) ya da .bk-note--plain.
  function note(tl, el, at) {
    tl.fromTo(q(el), { opacity: 0, scale: 0.9, x: -10 }, { opacity: 1, scale: 1, x: 0, duration: 0.3, ease: EASE.settle }, at);
    return tl;
  }

  // ================= Veri =================
  // Çubuklar soldan büyür (taşar, oturur). fills: .bk-bar-fill öğeleri; değerler ayrıca BK.count ile sayılabilir.
  function bars(tl, fills, at, o) {
    o = o || {};
    tl.fromTo(q(fills), { scaleX: 0, transformOrigin: "0% 50%" }, { scaleX: 1, duration: o.duration || 0.6, stagger: o.stagger == null ? 0.1 : o.stagger, ease: EASE.settle }, at);
    return tl;
  }
  // Kontrol listesi satırı: satır kayar, tik çizilir, (varsa) damga vurulur.
  function check(tl, row, at, o) {
    o = o || {};
    var r = one(row);
    rise(tl, r, at, { y: 0, duration: 0.3 });
    tl.fromTo(r.querySelector(".bk-check-tick"), { scaleY: 0, opacity: 0 }, { scaleY: 1, opacity: 1, duration: 0.25, ease: EASE.settle }, at + 0.15);
    var s = r.querySelector(".bk-stamp");
    if (s && !o.noStamp) stamp(tl, s, at + 0.3, { rotation: o.rotation == null ? -3 : o.rotation });
    return tl;
  }
  // Kart-ip-kart: SVG path çizilir (stroke-dash), uçtaki raptiyeler pop eder.
  function string(tl, path, at, o) {
    o = o || {};
    Array.prototype.forEach.call(q(path), function (p, i) {
      var L = Math.ceil(p.getTotalLength()) + 2;
      p.style.strokeDasharray = L + " " + L;
      tl.fromTo(p, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: o.duration || 0.55, ease: EASE.draw }, at + i * (o.stagger || 0.1));
    });
    if (o.pins) tl.fromTo(q(o.pins), { scale: 0 }, { scale: 1, duration: 0.3, stagger: 0.05, ease: EASE.pop }, at);
    return tl;
  }
  // Formül adım adım: parçalar (.bk-fx, .bk-op) sırayla pop eder.
  function formula(tl, parts, at, o) {
    o = o || {};
    tl.fromTo(q(parts), { opacity: 0, scale: 0.85, y: 14 }, { opacity: 1, scale: 1, y: 0, duration: 0.34, stagger: o.stagger == null ? 0.09 : o.stagger, ease: EASE.pop }, at);
    return tl;
  }

  // ================= Çerçeve =================
  // Üst şerit (sekme/teslimat etiketi, bölüm, numara), kesikli çizgi, başlık kelime kelime çarpar, repo satırı. 0..~1.0 sn.
  function frame(tl, root, at) {
    at = at || 0;
    var band = root.querySelectorAll(".bk-band > *");
    tl.fromTo(band, { opacity: 0, y: -20 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.06, ease: EASE.settle }, at);
    var rule = root.querySelector(".bk-rule");
    if (rule) draw(tl, rule, at + 0.1, { duration: 0.55 });
    var title = root.querySelector(".bk-title");
    if (title) titleIn(tl, title, at + 0.2);
    var repo = root.querySelector(".bk-repo");
    if (repo) tl.fromTo(repo, { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.4, ease: EASE.settle }, at + 0.5);
    return tl;
  }

  // ---- Canlı geçiş köprüsü ----
  // hyperframes-slideshow yalnız SEEK eder. Slideshow içinde ileri kısa atlamaları gerçek zamanda oynatır; varış karesi seek ile aynı.
  var LIVE = (function () {
    try {
      var fe = window.frameElement;
      if (!fe) return false;
      var host = fe.getRootNode && fe.getRootNode().host;
      var node = host || fe;
      return !!(node && node.closest && node.closest("hyperframes-slideshow"));
    } catch (e) { return false; }
  })();
  // Canlı modda GSAP lagSmoothing kapatılır: rAF kısıldığında (arka plan sekmesi, örtülü pencere) varsayılan ayar
  // her tiki ~33 ms ile sınırlar ve geçiş sürünür; kapalıyken geçiş duvar saatine göre zamanında biter.
  if (LIVE && window.gsap && window.gsap.ticker) window.gsap.ticker.lagSmoothing(0);
  function attachLive(tl, win) {
    if (!LIVE || !window.gsap) return;
    var orig = tl.totalTime;
    var anim = null, target = null;
    tl.totalTime = function (t, suppress) {
      if (!arguments.length) return orig.call(tl);
      var cur = orig.call(tl);
      if (anim && t === target) return tl;
      if (anim) { anim.kill(); anim = null; target = null; }
      var gap = t - cur;
      if (gap > 0.04 && t < win - 0.01) {
        var p = { v: cur };
        target = t;
        anim = window.gsap.to(p, {
          v: t, duration: gap, ease: "none",
          onUpdate: function () { orig.call(tl, p.v, true); },
          onComplete: function () { orig.call(tl, t, true); anim = null; target = null; }
        });
        return tl;
      }
      return orig.call(tl, t, suppress);
    };
  }

  // Sahne kaydı. Pencere: sahne kökündeki data-window (yoksa 8). build(tl, root, BK).
  function scene(id, build) {
    var stage = document.querySelector('[data-composition-id="' + id + '"] .bk-stage');
    var host = stage ? stage.closest('[data-composition-id="' + id + '"]') : null;
    var win = host && host.getAttribute("data-window") ? parseFloat(host.getAttribute("data-window")) : T.WINDOW;
    var tl = window.gsap.timeline({ paused: true });
    if (host) { layoutBursts(host); build(tl, host, BK); }
    tl.set({}, {}, win - 0.001);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
    attachLive(tl, win);
    return tl;
  }

  var BK = {
    T: T, EASE: EASE, DUR: DUR, rest: rest, stepAt: stepAt, plan: plan, live: LIVE,
    words: words, chars: chars, titleIn: titleIn, rise: rise, fade: fade, slam: slam, panelIn: panelIn, draw: draw,
    scan: scan, stamp: stamp, count: count, travel: travel, dim: dim, burst: burst,
    mascotIn: mascotIn, mascotReact: mascotReact, mascotSwap: mascotSwap,
    type: type, stream: stream, termMeta: termMeta, termMark: termMark, note: note,
    bars: bars, check: check, string: string, formula: formula,
    frame: frame, scene: scene
  };
  window.BK = BK;
})();
