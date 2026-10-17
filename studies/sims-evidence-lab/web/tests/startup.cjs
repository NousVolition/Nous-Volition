const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const runtime = fs.readFileSync(path.join(root, 'src/page-runtime.js'), 'utf8');
const seed = JSON.parse(fs.readFileSync(path.join(root, 'src/latest-run.json'), 'utf8'));
let checks = 0;
function check(value, label) { assert(value, label); checks++; }
function boot({ saved, denyRead = false, denyWrite = false, initial = seed } = {}) {
  const attrs = {};
  const status = { hidden: false, textContent: 'Loading SIMS', setAttribute(k,v) { attrs[k]=v; } };
  const model = { setAttribute(k,v) { attrs[k]=v; } };
  const stateElement = { textContent: JSON.stringify(initial), remove() {} };
  const writes = [], events = [];
  const sandbox = {
    document: { documentElement: { dataset: {} }, getElementById(id) { return {'sims-startup-status':status, 'sims-model':model, 'sims-initial-state':stateElement}[id]; } },
    location: { pathname: '/', search: '' },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    TextEncoder,
    CustomEvent: class { constructor(type, detail) { this.type=type; Object.assign(this,detail); } },
    dispatchEvent(event) { events.push(event); },
    console: { error() {} },
  };
  Object.defineProperty(sandbox, 'localStorage', { get() {
    if (denyRead) throw Error('Storage blocked');
    return { getItem: () => saved ?? null, setItem(k,v) { if (denyWrite) throw Error('Quota'); writes.push([k,v]); } };
  }});
  vm.createContext(sandbox);
  vm.runInContext(runtime, sandbox);
  return { sandbox, attrs, status, writes, events };
}
(async () => {
  const fresh = boot();
  check(fresh.sandbox.openai.widgetState.modelContent.config.seed === 20261011, 'first visit receives snapshot synchronously');
  check(fresh.sandbox.openai.widgetState.modelContent.config.roundCount === 8, 'eight rounds preserved');
  fresh.sandbox.simsPage.ready();
  check(fresh.status.hidden && fresh.attrs['aria-busy'] === 'false', 'successful startup hides loading message');
  check(fresh.sandbox.document.documentElement.dataset.simsReady === 'true', 'ready marker');
  const custom = structuredClone(seed); custom.modelContent.config.seed = 17;
  const persisted = boot({ saved: JSON.stringify(custom) });
  check(persisted.sandbox.openai.widgetState.modelContent.config.seed === 17, 'existing settings override snapshot');
  for (const saved of ['{broken', 'null', '[]', '42', JSON.stringify({oversized:'x'.repeat(17000)})]) {
    check(boot({ saved }).sandbox.openai.widgetState.modelContent.config.seed === 20261011, 'bad storage falls back safely');
  }
  const denied = boot({ denyRead: true });
  check(denied.sandbox.openai.widgetState.modelContent.config.seed === 20261011, 'storage denied still starts');
  await denied.sandbox.openai.setWidgetState(custom);
  check(denied.sandbox.openai.widgetState.modelContent.config.seed === 17, 'storage denied still permits interaction');
  const quota = boot({ denyWrite: true });
  await quota.sandbox.openai.setWidgetState(custom);
  check(quota.sandbox.openai.statePersistence === 'none', 'quota failure does not stop interaction');
  await fresh.sandbox.openai.setWidgetState(custom);
  check(fresh.writes[0][0] === 'codex:visualization-widget-state-v2:["/",""]', 'legacy storage key retained');
  check(JSON.parse(fresh.writes[0][1]).modelContent.config.seed === 17, 'settings saved');
  check(fresh.events[0].type === 'openai:set_globals', 'model receives state event');
  check(boot({ initial: null }).sandbox.openai.widgetState === null, 'other pages use their defaults');
  const failed = boot(); failed.sandbox.simsPage.failed(new Error('Example'));
  check(!failed.status.hidden && failed.attrs.role === 'alert', 'startup error is visible');
  for (const file of fs.readdirSync(path.join(root, 'dist')).filter(f=>f.endsWith('.html'))) {
    const html = fs.readFileSync(path.join(root, 'dist',file), 'utf8');
    check(!/<iframe\b|data-srcdoc=|new\s+MessageChannel\b/.test(html), file+' has no frame startup');
    check(!/<script\b[^>]*\bsrc\s*=/.test(html), file+' has no remote script dependency');
    check(html.includes('data-sims-host="direct-v2"') && html.includes('<h3'), file+' includes model in initial response');
    check(html.indexOf('globalThis.openai =') < html.indexOf('const N=9') || file==='sims-network.html', file+' initializes state before model');
    check(html.includes('<noscript>'), file+' has non-JS message');
    for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
  }
  console.log(JSON.stringify({passed:true,checks,coverage:['fresh and saved state','corrupt or denied storage','startup error visibility','six pages without iframe or remote scripts','script syntax']}));
})().catch(error => { console.error(error); process.exitCode=1; });
