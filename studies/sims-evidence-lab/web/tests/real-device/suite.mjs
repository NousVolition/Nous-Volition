import assert from 'node:assert/strict';
import path from 'node:path';
import {Controls, pause} from './controls.mjs';

export async function runSuite(session, {base, revision, output, check}) {
  const c = new Controls(session), s = session;
  const routes = ['', 'sims-evidence-and-response.html', 'sims-claim-testing.html', 'sims-network.html', 'sims-repeated-rounds.html', 'latest-run.html'];
  for (const route of routes) {
    const test = (name, fn) => check(route || 'Latest run', name, fn);
    await s.go(new URL(route, base).href);
    if (!await test('loads without refresh and fits viewport', () => c.ready(revision))) continue;
    await s.screenshot(path.join(output, (route.replace('.html', '') || 'latest') + '-loaded.png'));
    if (route === 'sims-repeated-rounds.html' || route === 'latest-run.html') continue;
    await s.js(() => {
      window.__simsTouches = []; window.__simsErrors = [];
      document.addEventListener('pointerdown', e => window.__simsTouches.push({trusted: e.isTrusted, type: e.pointerType, action: e.target.closest('[data-action]')?.dataset.action}), true);
      window.addEventListener('error', e => window.__simsErrors.push(e.message));
      window.addEventListener('unhandledrejection', e => window.__simsErrors.push(String(e.reason)));
    });
    const exchange = await s.js(() => !!document.querySelector('[data-action="exchange"]'));
    if (exchange) await c.tap('[data-action="exchange"]');
    const summaries = await s.js(() => [...document.querySelectorAll('summary')].filter(e => e.getBoundingClientRect().width > 0).map((e, i) => { e.dataset.ciSummary = String(i); return {i, text: e.textContent.trim()}; }));
    for (const {i, text} of summaries) await test('disclosure: ' + text, async () => {
      const sel = `[data-ci-summary="${i}"]`, before = await s.js(sel => document.querySelector(sel).parentElement.open, sel);
      await c.tap(sel); const after = await s.js(sel => document.querySelector(sel).parentElement.open, sel);
      assert.notEqual(after, before); if (!after) await c.tap(sel); return {before, after};
    });
    const selects = await s.js(() => [...document.querySelectorAll('select[data-control]')].map(e => ({name: e.dataset.control, value: e.value, options: [...e.options].filter(o => !o.disabled && o.value !== 'custom').map(o => o.value)})));
    for (const field of selects) await test('select ' + field.name, async () => {
      const value = field.options.find(v => v !== field.value) ?? field.value; await c.select(field.name, value); return {value};
    });
    if (selects.some(f => f.name === 'preset')) await c.select('preset', selects.find(f => f.name === 'preset').options.includes('contrast') ? 'contrast' : 'mismatch');
    if (selects.some(f => f.name === 'round')) await c.select('round', '0');
    for (const name of await s.js(() => [...document.querySelectorAll('input[type="checkbox"]')].map(e => e.dataset.control))) await test('checkbox ' + name, async () => {
      const sel = `input[data-control="${name}"]`; await c.ensure(sel);
      const before = await s.js(sel => document.querySelector(sel).checked, sel); await c.tap(sel + ' + span');
      assert.notEqual(await s.js(sel => document.querySelector(sel).checked, sel), before);
    });
    if (!await test('native keyboard seed entry', () => c.seed())) {
      // Keep the failed assertion, but recover focus before unrelated touch checks.
      await s.go(new URL(route, base).href); await c.ready(revision);
    }
    await test('New trial uses committed seed', async () => {
      await c.ensure('[data-action="new"]'); const before = (await c.snapshot()).seed;
      await c.tap('[data-action="new"]'); const after = (await c.snapshot()).seed;
      assert.equal(Number(after), Number(before) === 2147483647 ? 1 : Number(before) + 1); return {before, after};
    });
    if (exchange) for (const stage of ['before', 'exchange', 'after']) await test('stage ' + stage, async () => {
      await c.tap(`[data-action="${stage}"]`);
      assert.equal(await s.js(sel => document.querySelector(sel).getAttribute('aria-pressed'), `[data-action="${stage}"]`), 'true');
      return c.snapshot();
    });
    if (exchange) await c.tap('[data-action="exchange"]');
    await test('slider thumb touch drag', () => c.slider());
    await test('touch step', async () => {
      const before = await c.snapshot(); await c.tap('[data-action="step"]'); const after = await c.snapshot();
      assert.notEqual(after.cursor, before.cursor); return {before, after};
    });
    await test('touch play and pause', async () => {
      await c.tap('[data-action="play"]'); const playing = await c.snapshot(); assert.match(playing.play, /pause/i);
      await c.tap('[data-action="play"]'); const stopped = await c.snapshot(); assert.doesNotMatch(stopped.play, /pause/i);
      return {playing, stopped};
    });
    if (await s.js(() => !!document.querySelector('[data-action="finish"]'))) await test('touch finish', async () => {
      await c.tap('[data-action="finish"]'); const range = await s.js(() => { const e = document.querySelector('input[type="range"]'); return {value: e.value, max: e.max}; });
      assert.equal(range.value, range.max); return range;
    });
    const participants = await s.js(() => [...document.querySelectorAll('button[aria-label^="Inspect SIM"]')].map((e, i) => { e.dataset.ciParticipant = String(i); return {i, label: e.getAttribute('aria-label')}; }));
    for (const p of participants) await test('touch ' + p.label + ' row ' + p.i, async () => {
      await c.tap(`[data-ci-participant="${p.i}"]`); const selected = (await c.snapshot()).selected;
      assert.ok(selected?.includes(p.label.replace('Inspect ', ''))); return selected;
    });
    if (exchange) await test('read participant exchange', async () => {
      const selected = (await c.snapshot()).selected;
      await c.tap('[data-action="read-reply"]');
      assert.equal(await s.js(() => document.querySelector('[data-action="exchange"]').getAttribute('aria-pressed')), 'true');
      assert.equal((await c.snapshot()).selected, selected);
    });
    if (route === 'sims-claim-testing.html') await test('last tested decision', async () => {
      await c.tap('[data-action="finish"]'); await c.tap('[data-action="jump"]');
      assert.match((await c.snapshot()).phase, /Observation/);
      assert.equal(Number((await c.snapshot()).cursor) % 2, 1);
    });
    if (route === '') await c.select('round-count', '8');
    const tables = await s.js(() => [...document.querySelectorAll('.sims-table-scroll')].map((e, i) => { e.dataset.ciTable = String(i); return {i, overflow: e.scrollWidth > e.clientWidth + 1}; }).filter(t => t.overflow));
    for (const table of tables) await test('sideways table swipe ' + table.i, async () => {
      const sel = `[data-ci-table="${table.i}"]`; await c.ensure(sel); await c.point(sel);
      await s.js(sel => document.querySelector(sel).scrollLeft = 0, sel);
      const p = await s.js(sel => { const r = document.querySelector(sel).getBoundingClientRect(); return {left: r.left, right: r.right, y: Math.min(innerHeight - 45, Math.max(45, r.top + 25))}; }, sel);
      await c.touch([{type: 'pointerMove', duration: 0, x: p.right - 25, y: p.y}, {type: 'pointerDown', button: 0}, {type: 'pointerMove', duration: 650, x: p.left + 35, y: p.y}, {type: 'pointerUp', button: 0}]);
      const scrollLeft = await s.js(sel => document.querySelector(sel).scrollLeft, sel); assert.ok(scrollLeft > 0); return {scrollLeft};
    });
    await test('vertical touch swipe', async () => {
      await s.js(() => scrollTo(0, 0)); const v = await s.js(() => ({width: innerWidth, height: innerHeight}));
      await c.touch([{type: 'pointerMove', duration: 0, x: v.width - 30, y: v.height - 80}, {type: 'pointerDown', button: 0}, {type: 'pointerMove', duration: 650, x: v.width - 30, y: 100}, {type: 'pointerUp', button: 0}]);
      assert.ok(await s.js(() => scrollY > 0));
    });
    await test('tap tooltip and dismiss', async () => {
      const text = await s.js(() => { const a = [...document.querySelectorAll('[data-tooltip]')].filter(e => e.getBoundingClientRect().width > 0 && e.getBoundingClientRect().height > 0); const e = a.find(e => e.classList.contains('history-code')) || a[0]; if (!e) return null; e.dataset.ciTooltip = '1'; return e.getAttribute('data-tooltip'); });
      assert.ok(text, 'No visible tooltip target'); await c.tap('[data-ci-tooltip="1"]');
      await c.waitFor(() => s.js(() => document.querySelector('[role="tooltip"]')?.textContent).then(v => v === text), 'Tooltip did not open');
      await c.tap('.sims-brand'); await c.waitFor(() => s.js(() => !document.querySelector('[role="tooltip"]')), 'Tooltip did not dismiss');
      return text;
    });
    await test('trusted touch events reached controls', async () => {
      const events = await s.js(() => window.__simsTouches.filter(e => e.action));
      assert.ok(events.some(e => e.trusted && e.type === 'touch')); return events.slice(0, 12);
    });
    await test('no interaction runtime errors', async () => { const errors = await s.js(() => window.__simsErrors); assert.deepEqual(errors, []); });
  }

  await s.go(base); await c.ready(revision);
  const links = await s.js(() => [...document.querySelectorAll('.sims-links a')].map(e => ({text: e.textContent, href: e.href})));
  assert.equal(links.length, 7, 'Expected all seven SIMS navigation links');
  for (const link of links) await check('Navigation', link.text, async () => {
    await s.go(base); await c.ready(revision); const before = await s.command('GET', '/window/handles');
    await s.js(href => { [...document.querySelectorAll('.sims-links a')].find(e => e.href === href).dataset.ciLink = '1'; }, link.href);
    await c.tap('[data-ci-link="1"]'); await pause(500);
    const after = await s.command('GET', '/window/handles'), newHandle = after.find(h => !before.includes(h));
    try {
      if (newHandle) await s.command('POST', '/window', {handle: newHandle});
      const info = await s.js(() => ({url: location.href, title: document.title, body: document.body.innerText.slice(0, 250)}));
      assert.doesNotMatch(info.title + ' ' + info.body, /404|page not found|site can.t be reached/i);
      if (new URL(link.href).origin === new URL(base).origin) await c.ready(revision);
      else { assert.ok(info.url.startsWith('https://github.com/NousVolition/Nous-Volition/')); assert.ok(info.url.includes(link.text === 'Methods' ? 'METHODS.md' : 'studies/sims-evidence-lab')); }
      return {url: info.url, title: info.title};
    } finally { if (newHandle) { await s.command('DELETE', '/window'); await s.command('POST', '/window', {handle: before[0]}); } }
  });
  await s.go(new URL('sims-network.html', base).href); await c.ready(revision);
  try {
    await c.rotate('LANDSCAPE');
    await check('Rotation', 'landscape layout and touch step', async () => {
      const layout = await c.ready(revision); assert.ok(layout.width > layout.height);
      const before = await c.snapshot(); await c.tap('[data-action="step"]'); const after = await c.snapshot();
      assert.notEqual(after.cursor, before.cursor);
      await s.screenshot(path.join(output, 'landscape.png')); return {layout, before, after};
    });
  } finally { await c.rotate('PORTRAIT'); }
  await check('Rotation', 'portrait restored', async () => { const layout = await c.ready(revision); assert.ok(layout.height > layout.width); return layout; });
  await s.go(base); await c.ready(revision); await s.screenshot(path.join(output, 'final.png'));
}
