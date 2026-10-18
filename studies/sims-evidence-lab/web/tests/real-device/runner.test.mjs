import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {credentials} from './credentials.mjs';
import {DeviceSession, unwrap} from './session.mjs';
import {pages, serveBuild} from './server.mjs';

test('missing credentials fail with names, never values', () => {
  assert.throws(() => credentials({}), /BROWSERSTACK_USERNAME/);
  assert.throws(() => credentials({BROWSERSTACK_USERNAME: 'example'}), /BROWSERSTACK_ACCESS_KEY/);
  assert.deepEqual(credentials({BROWSERSTACK_USERNAME: 'u', BROWSERSTACK_ACCESS_KEY: 'k'}), {user: 'u', key: 'k'});
});
test('WebDriver null stays null', () => {
  assert.equal(unwrap({value: null}), null);
  assert.equal(unwrap({value: false}), false);
  assert.equal(unwrap({value: 0}), 0);
  assert.deepEqual(unwrap({sessionId: 'example'}), {sessionId: 'example'});
});
test('capabilities require a real phone, pin versions and identify the tunnel', async () => {
  for (const device of ['iphone', 'android']) {
    const requests = [];
    const session = new DeviceSession({user: 'example-user', key: 'example-key', device, localIdentifier: 'test-tunnel', buildName: 'test-build'}, async (url, options) => {
      requests.push({url, ...options});
      return {ok: true, json: async () => ({value: url.endsWith('/session') ? {sessionId: 'fake', capabilities: {}} : null})};
    });
    await session.start();
    const caps = JSON.parse(requests[0].body).capabilities.alwaysMatch;
    assert.equal(caps['bstack:options'].realMobile, 'true');
    assert.equal(caps['bstack:options'].localIdentifier, 'test-tunnel');
    assert.equal(caps['bstack:options'].local, 'true');
    assert.equal(caps.browserName, device === 'iphone' ? 'safari' : 'chrome');
    assert.equal(caps['bstack:options'].deviceName, device === 'iphone' ? 'iPhone 16' : 'Samsung Galaxy S23');
    await session.close(); assert.equal(session.id, null); assert.equal(requests.at(-1).method, 'DELETE');
  }
});
test('provider failures remain failures and secrets are redacted', async () => {
  const s = new DeviceSession({user: 'example-user', key: 'example-key', device: 'iphone'}, async () => ({ok: false, json: async () => ({value: {error: 'invalid', message: 'example-user example-key denied'}})}));
  await assert.rejects(s.start(), /\[redacted\] \[redacted\] denied/);
  assert.throws(() => new DeviceSession({user: 'u', key: 'k', device: 'emulator'}), /iphone or android/);
});
test('build server exposes only built pages and marks the checked-out revision', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'sims-ci-contract-'));
  let server;
  try {
    for (const file of pages) await fs.writeFile(path.join(root, file), '<html><head></head><body>SIMS</body></html>');
    await fs.writeFile(path.join(root, 'private.txt'), 'not served');
    server = await serveBuild(root, 'abc123', 0);
    const base = `http://127.0.0.1:${server.address().port}`;
    for (const route of ['', 'latest-run', 'sims-network.html']) {
      const response = await fetch(base + '/' + route); assert.equal(response.status, 200);
      assert.match(await response.text(), /name="sims-ci-revision" content="abc123"/);
      assert.equal(response.headers.get('cache-control'), 'no-store');
    }
    for (const route of ['private.txt', '.env', 'missing']) assert.equal((await fetch(base + '/' + route)).status, 404);
    assert.equal((await fetch(base + '/', {method: 'POST'})).status, 404);
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    assert.equal(path.dirname(path.resolve(root)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('sims-ci-contract-'));
    await fs.rm(root, {recursive: true, force: true});
  }
});
