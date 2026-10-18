import fs from 'node:fs/promises';

export const devices = {
  iphone: {browserName: 'safari', deviceName: 'iPhone 16', osVersion: '18.5'},
  android: {browserName: 'chrome', deviceName: 'Samsung Galaxy S23', osVersion: '13.0'},
};
export const unwrap = data => Object.hasOwn(data, 'value') ? data.value : data;
export const elementId = el => el['element-6066-11e4-a52e-4f735466cecf'] || el.ELEMENT;

export class DeviceSession {
  constructor({user, key, device, localIdentifier, buildName}, transport = fetch) {
    if (!devices[device]) throw new Error('SIMS_DEVICE must be iphone or android');
    this.device = device;
    this.spec = devices[device];
    this.localIdentifier = localIdentifier;
    this.buildName = buildName;
    this.id = null;
    this.transport = transport;
    this.auth = 'Basic ' + Buffer.from(user + ':' + key).toString('base64');
    this.secrets = [user, key, this.auth, this.auth.slice(6)].filter(Boolean);
  }
  sanitize(value) {
    let text = String(value);
    for (const secret of this.secrets) text = text.split(secret).join('[redacted]');
    return text;
  }
  async request(method, path, body, timeout = 60000) {
    const response = await this.transport('https://hub-cloud.browserstack.com/wd/hub' + path, {
      method, headers: {Authorization: this.auth, 'Content-Type': 'application/json'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
      signal: AbortSignal.timeout(timeout),
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error(`BrowserStack returned a non-JSON HTTP ${response.status} response`); }
    if (!response.ok || data.value?.error) throw new Error(this.sanitize(data.value?.message || data.message || `HTTP ${response.status}`));
    return unwrap(data);
  }
  async start() {
    const {browserName, deviceName, osVersion} = this.spec;
    const result = await this.request('POST', '/session', {capabilities: {alwaysMatch: {
      browserName, 'bstack:options': {
        deviceName, osVersion, realMobile: 'true', projectName: 'SIMS Evidence Lab',
        buildName: this.buildName, sessionName: `SIMS ${this.device} touch controls`,
        idleTimeout: 120, debug: true, video: true,
        ...(this.localIdentifier ? {local: 'true', localIdentifier: this.localIdentifier} : {}),
      },
    }, firstMatch: [{}]}}, 180000);
    this.id = result.sessionId;
    if (!this.id) throw new Error('BrowserStack did not create a device session');
    await this.command('POST', '/timeouts', {implicit: 0, pageLoad: 60000, script: 30000});
    return {sessionId: this.id, requested: this.spec, platform: result.capabilities?.platformName,
      platformVersion: result.capabilities?.platformVersion, browser: result.capabilities?.browserName};
  }
  command(method, path, body) { return this.request(method, '/session/' + this.id + path, body); }
  execute(script, args = []) { return this.command('POST', '/execute/sync', {script, args}); }
  js(fn, ...args) { return this.execute('return (' + fn.toString() + ')(...arguments)', args); }
  go(url) { return this.command('POST', '/url', {url}); }
  async element(css) { return elementId(await this.command('POST', '/element', {using: 'css selector', value: css})); }
  async click(css) { return this.command('POST', '/element/' + await this.element(css) + '/click', {}); }
  async screenshot(file) { const png = await this.command('GET', '/screenshot'); await fs.writeFile(file, Buffer.from(png, 'base64')); }
  executor(action, args = {}) { return this.execute('browserstack_executor: ' + JSON.stringify({action, arguments: args})); }
  async close() {
    if (!this.id) return;
    const id = this.id;
    await this.request('DELETE', '/session/' + id, undefined, 15000);
    this.id = null;
  }
}
