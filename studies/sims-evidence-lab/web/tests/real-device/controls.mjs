import assert from 'node:assert/strict';
import {elementId} from './session.mjs';
export const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

export class Controls {
  constructor(session) { this.s = session; this.offset = {x: 0, y: session.device === 'iphone' ? 59 : 0}; }
  async waitFor(fn, message, timeout = 10000) {
    const end = Date.now() + timeout;
    do { if (await fn()) return; await pause(200); } while (Date.now() < end);
    throw new Error(message);
  }
  async ready(revision) {
    await this.waitFor(() => this.s.js(() => document.documentElement.dataset.simsReady === 'true'), 'SIMS did not become ready on first navigation');
    const state = await this.s.js(() => ({ready: document.documentElement.dataset.simsReady,
      busy: document.querySelector('main')?.getAttribute('aria-busy'), width: innerWidth, height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth, touch: navigator.maxTouchPoints, title: document.title,
      revision: document.querySelector('meta[name="sims-ci-revision"]')?.content}));
    assert.equal(state.busy, 'false'); assert.ok(state.touch > 0); assert.ok(state.scrollWidth <= state.width + 1, 'Horizontal page overflow');
    if (revision) assert.equal(state.revision, revision, 'Phone must test the checked-out commit');
    return state;
  }
  async touch(points, raw = false) {
    await this.s.command('POST', '/actions', {actions: [{type: 'pointer', id: 'finger', parameters: {pointerType: 'touch'}, actions: points.map(p => p.type === 'pointerMove' ? {...p, origin: 'viewport', x: Math.round(p.x + (raw ? 0 : this.offset.x)), y: Math.round(p.y + (raw ? 0 : this.offset.y))} : p)}]});
    await pause(250);
  }
  async point(selector) {
    await this.s.js(sel => { const e = document.querySelector(sel); if (!e) throw new Error('Missing ' + sel); e.scrollIntoView({block: 'center', inline: 'center'}); }, selector);
    await pause(150);
    const p = await this.s.js(sel => { const e = document.querySelector(sel), r = e.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2, left: r.left, right: r.right, width: r.width, height: r.height, value: e.value, min: e.min, max: e.max, disabled: e.disabled}; }, selector);
    assert.ok(p.width > 0 && p.height > 0, 'Control is hidden: ' + selector);
    assert.ok(!p.disabled, 'Control is disabled: ' + selector);
    return p;
  }
  async tap(selector) {
    const p = await this.point(selector);
    await this.touch([{type: 'pointerMove', duration: 0, x: p.x, y: p.y}, {type: 'pointerDown', button: 0}, {type: 'pause', duration: 80}, {type: 'pointerUp', button: 0}]);
  }
  async ensure(selector) {
    const parents = await this.s.js(sel => { const parents = []; for (let e = document.querySelector(sel); e; e = e.parentElement) if (e.tagName === 'DETAILS' && !e.open) { e.dataset.ciDetails = String([...document.querySelectorAll('details')].indexOf(e)); parents.unshift(e.dataset.ciDetails); } return parents; }, selector);
    for (const id of parents) await this.tap(`[data-ci-details="${id}"]>summary`);
  }
  async select(name, value) {
    const selector = `select[data-control="${name}"]`;
    await this.ensure(selector); await this.point(selector);
    await this.s.click(selector + ' option[value=' + JSON.stringify(value) + ']');
    await this.waitFor(() => this.s.js(sel => document.querySelector(sel).value, selector).then(v => v === value), 'Selection did not commit: ' + name);
  }
  snapshot() { return this.s.js(() => ({phase: document.querySelector('[data-display="phase"]')?.textContent, cursor: document.querySelector('input[type="range"]')?.value, selected: document.querySelector('[data-display="selected-title"]')?.textContent, seed: document.querySelector('[data-control="seed"]')?.value, play: document.querySelector('[data-action="play"]')?.textContent, round: document.querySelector('[data-control="round"]')?.value})); }
  async slider() {
    const p = await this.point('input[type="range"]');
    const fraction = (Number(p.value) - Number(p.min)) / (Number(p.max) - Number(p.min));
    const start = p.left + 14 + (p.width - 28) * fraction;
    const end = p.left + 14 + (p.width - 28) * (fraction > .5 ? .15 : .75);
    await this.touch([{type: 'pointerMove', duration: 0, x: start, y: p.y}, {type: 'pointerDown', button: 0}, {type: 'pause', duration: 120}, {type: 'pointerMove', duration: 700, x: end, y: p.y}, {type: 'pointerUp', button: 0}]);
    const after = await this.s.js(() => document.querySelector('input[type="range"]').value);
    assert.notEqual(after, p.value, 'Dragging slider thumb did not change the model');
    return {before: p.value, after};
  }
  async seed(value = '20261037') {
    await this.ensure('[data-control="seed"]');
    const before = (await this.snapshot()).seed;
    await this.tap('[data-control="seed"]');
    const context = await this.s.command('GET', '/context');
    try {
      await this.s.command('POST', '/context', {name: 'NATIVE_APP'});
      if (this.s.device === 'iphone') {
        const query = {using: '-ios predicate string', value: "type == 'XCUIElementTypeTextField' AND label == 'Trial seed'"};
        let id = elementId(await this.s.command('POST', '/element', query));
        await this.s.command('POST', '/element/' + id + '/clear', {});
        id = elementId(await this.s.command('POST', '/element', query));
        await this.s.command('POST', '/element/' + id + '/value', {text: value, value: [...value]});
        const done = elementId(await this.s.command('POST', '/element', {using: 'accessibility id', value: 'Done'}));
        await this.s.command('POST', '/element/' + done + '/click', {});
      } else {
        await this.s.command('POST', '/appium/device/press_keycode', {keycode: 123});
        for (let i = 0; i < before.length; i++) await this.s.command('POST', '/appium/device/press_keycode', {keycode: 67});
        for (const digit of value) await this.s.command('POST', '/appium/device/press_keycode', {keycode: 7 + Number(digit)});
        await this.s.command('POST', '/appium/device/press_keycode', {keycode: 66});
      }
    } finally { await this.s.command('POST', '/context', {name: context}); }
    await this.tap('.sims-brand');
    assert.equal((await this.snapshot()).seed, value, 'Native keyboard seed did not commit');
    return {before, after: value};
  }
  async rotate(orientation) {
    await this.s.command('POST', '/orientation', {orientation}); await pause(500);
    this.offset = {x: 0, y: this.s.device === 'iphone' ? 59 : 0};
    if (orientation === 'LANDSCAPE') {
      await this.s.js(() => { window.__simsCalibration = null; document.addEventListener('pointerdown', e => window.__simsCalibration = {x: e.clientX, y: e.clientY, trusted: e.isTrusted, type: e.pointerType}, {once: true}); });
      await this.touch([{type: 'pointerMove', duration: 0, x: 300, y: 200}, {type: 'pointerDown', button: 0}, {type: 'pointerUp', button: 0}], true);
      const cal = await this.s.js(() => window.__simsCalibration);
      assert.ok(cal && cal.trusted && cal.type === 'touch', 'Landscape touch calibration failed');
      this.offset = {x: 300 - cal.x, y: 200 - cal.y};
    }
  }
}
