(() => {
  const root = document.documentElement;
  const status = document.getElementById('sims-startup-status');
  const model = document.getElementById('sims-model');
  const stateElement = document.getElementById('sims-initial-state');
  const storageKey = `codex:visualization-widget-state-v2:${JSON.stringify([
    globalThis.location.pathname, globalThis.location.search,
  ])}`;
  const validate = (value) => {
    if (value == null || typeof value !== 'object' || Array.isArray(value)) {
      throw new TypeError('SIMS settings must be an object');
    }
    const serialized = JSON.stringify(value, (_key, item) => {
      if (typeof item === 'number' && !Number.isFinite(item)) {
        throw new TypeError('SIMS settings must contain finite numbers');
      }
      return item;
    });
    if (new TextEncoder().encode(serialized).length > 16 * 1024) {
      throw new TypeError('SIMS settings are too large');
    }
    return JSON.parse(serialized);
  };
  let state = null;
  try {
    const initial = JSON.parse(stateElement?.textContent || 'null');
    if (initial != null) state = validate(initial);
  } catch { /* The model's built-in defaults remain available. */ }
  stateElement?.remove();

  let storage = null;
  try {
    storage = globalThis.localStorage;
    const saved = storage.getItem(storageKey);
    if (saved != null) {
      try { state = validate(JSON.parse(saved)); }
      catch { /* Corrupt saved settings must not prevent first render. */ }
    }
  } catch { storage = null; }

  const media = globalThis.matchMedia('(prefers-color-scheme: dark)');
  const publishState = () => globalThis.dispatchEvent(new CustomEvent(
    'openai:set_globals', { detail: { globals: globalThis.openai } },
  ));
  // Keep the model's state interface and existing browser storage keys. The
  // model is ordinary page content; it no longer waits for an iframe load or
  // a transferred MessageChannel before it can render or save settings.
  globalThis.openai = {
    widgetState: state,
    statePersistence: storage ? 'local' : 'none',
    stateModelContext: 'none',
    visualizationStyleVariables: {},
    async setWidgetState(next) {
      state = validate(typeof next === 'function' ? next(state) : next);
      globalThis.openai.widgetState = state;
      publishState();
      if (storage) {
        try { storage.setItem(storageKey, JSON.stringify(state)); }
        catch { globalThis.openai.statePersistence = 'none'; }
      }
    },
  };
  const theme = () => {
    const name = media.matches ? 'dark' : 'light';
    root.dataset.theme = name;
    globalThis.openai.theme = name;
    globalThis.openai.visualizationTheme = name;
  };
  theme();
  media.addEventListener('change', theme);

  globalThis.simsPage = {
    ready() {
      root.dataset.simsReady = 'true';
      model.setAttribute('aria-busy', 'false');
      status.hidden = true;
    },
    failed(error) {
      root.dataset.simsReady = 'false';
      model.setAttribute('aria-busy', 'false');
      status.hidden = false;
      status.setAttribute('role', 'alert');
      status.textContent = 'SIMS could not start. Try opening another model using the links above.';
      console.error('SIMS startup failed', error);
    },
  };
})();
