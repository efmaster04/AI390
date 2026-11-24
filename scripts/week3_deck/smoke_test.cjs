// Opens the built single-file deck over file:// in headless Chrome (the one HyperFrames installs), steps through
// every fragment with ArrowRight, opens every Q&A hotspot, steps back, and reports page errors and any non-local request.
// Usage: node scripts/week3_deck/smoke_test.cjs docs/week3/index.html <screenshot dir> [sceneId,sceneId,...]
const fs = require('fs'), path = require('path'), os = require('os');
const pc = require(path.join(os.homedir(), '.npm-global/lib/node_modules/hyperframes/node_modules/puppeteer-core'));
const root = path.join(os.homedir(), '.cache/hyperframes/chrome/chrome-headless-shell');
const ver = fs.readdirSync(root)[0];
const exe = path.join(root, ver, fs.readdirSync(path.join(root, ver))[0], 'chrome-headless-shell');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const [file, out, only] = process.argv.slice(2);
  const want = only ? new Set(only.split(',')) : null;
  fs.mkdirSync(out, { recursive: true });
  const b = await pc.launch({ executablePath: exe, args: ['--allow-file-access-from-files'] });
  const pg = await b.newPage();
  await pg.setViewport({ width: 1920, height: 1080 });
  const errs = [], ext = [];
  pg.on('pageerror', e => errs.push(String(e)));
  pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  pg.on('request', r => { const u = r.url(); if (!/^(file|data|about|blob):/.test(u)) ext.push(u); });
  await pg.goto('file://' + path.resolve(file), { waitUntil: 'load' });
  await sleep(7000);
  await pg.focus('hyperframes-slideshow').catch(() => {});
  const pos = () => pg.evaluate(() => {
    const c = document.querySelector('hyperframes-slideshow').controller;
    const p = c.position, s = c.currentSlide;
    return { seq: p.sequenceId, i: p.slideIndex, f: p.fragmentIndex, id: s && s.sceneId, n: s ? s.fragments.length : 0, hs: s && s.hotspots ? s.hotspots.length : 0 };
  });
  const visited = [];
  let p = await pos(), guard = 0;
  while (guard++ < 200) {
    const name = `${String(p.i + 1).padStart(2, '0')}-${p.id}-f${p.f + 1}`;
    visited.push(name);
    if (!want || want.has(p.id)) await pg.screenshot({ path: path.join(out, name + '.png') });
    if (p.hs) break; // the questions slide holds the hotspots
    await pg.keyboard.press('ArrowRight');
    await sleep(1500);
    const q = await pos();
    if (q.i === p.i && q.f === p.f) break;
    p = q;
  }
  const branches = [];
  const pills = await pg.$$('pierce/.hf-hotspot-pill');
  for (let k = 0; k < pills.length; k++) {
    const all = await pg.$$('pierce/.hf-hotspot-pill');
    await all[k].click();
    await sleep(2500);
    const q = await pos();
    await pg.keyboard.press('ArrowRight'); await sleep(1500);
    const q2 = await pos();
    await pg.screenshot({ path: path.join(out, `q${k + 1}-${q.id}.png`) });
    branches.push(`${q.seq}:${q.id} f${q2.f + 1}/${q2.n}`);
    for (let j = 0; j < 4; j++) { const r = await pos(); if (r.seq === 'main') break; await pg.keyboard.press('ArrowLeft'); await sleep(900); }
  }
  const back = await pos();
  for (let j = 0; j < 9; j++) { await pg.keyboard.press('ArrowLeft'); await sleep(700); }
  await sleep(1500);
  const bp = await pos();
  await pg.screenshot({ path: path.join(out, `back-${bp.i + 1}-${bp.id}-f${bp.f + 1}.png`) });
  console.log(JSON.stringify({ steps: visited.length, last: visited[visited.length - 1], branches, returnedTo: `${back.seq}:${back.id}`,
    afterBack: `${bp.id} f${bp.f + 1}`, errors: errs.slice(0, 8), external: ext.slice(0, 8) }, null, 1));
  await b.close();
})();
