import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {credentials} from './credentials.mjs';
import {DeviceSession} from './session.mjs';
import {serveBuild} from './server.mjs';
import {runSuite} from './suite.mjs';

const web = fileURLToPath(new URL('../../', import.meta.url));
const device = process.env.SIMS_DEVICE || 'iphone';
const target = process.env.SIMS_TARGET || 'build';
if (!['build', 'live'].includes(target)) throw new Error('SIMS_TARGET must be build or live');
const revision = process.env.GITHUB_SHA || 'local';
const output = path.join(web, 'test-results/real-device', device);
await fs.mkdir(output, {recursive: true});
const report = {device, target, revision, started: new Date().toISOString(), checks: []};
let session, server, closing, interrupted = false;
const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'}[c]));
const save = () => fs.writeFile(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
async function cleanup() {
  if (closing) return closing;
  closing = (async () => {
    if (session?.id) { try { await session.close(); } catch (error) { report.cleanupError = session.sanitize(error.message); process.exitCode = 1; } }
    if (server) await new Promise(resolve => server.close(resolve));
  })();
  return closing;
}
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => {
  interrupted = true; report.interrupted = signal;
  await cleanup(); await save(); process.exit(1);
});
try {
  const localIdentifier = target === 'build' ? process.env.BROWSERSTACK_LOCAL_IDENTIFIER : undefined;
  if (target === 'build' && !localIdentifier) throw new Error('Start a BrowserStack Local tunnel and set BROWSERSTACK_LOCAL_IDENTIFIER before testing a build.');
  const base = target === 'build' ? 'http://bs-local.com:8000/' : 'https://sims-evidence-lab.itswaffles88.chatgpt.site/';
  report.baseUrl = base;
  session = new DeviceSession({...credentials(), device, localIdentifier, buildName: `SIMS ${process.env.GITHUB_RUN_ID || 'manual'} attempt ${process.env.GITHUB_RUN_ATTEMPT || '1'} ${revision.slice(0, 12)}`});
  if (target === 'build') server = await serveBuild(path.join(web, 'dist'), revision);
  report.session = await session.start(); await save();
  const check = async (route, name, fn) => {
    const start = Date.now(); let result;
    try { const details = await fn(); result = {route, name, passed: true, details}; }
    catch (error) {
      result = {route, name, passed: false, error: session.sanitize(error.message)};
      const filename = `failure-${report.checks.length + 1}.png`;
      try { await session.screenshot(path.join(output, filename)); result.screenshot = filename; } catch { /* Preserve the original assertion failure. */ }
    }
    result.seconds = (Date.now() - start) / 1000;
    report.checks.push(result); await save(); console.log(`${result.passed ? 'PASS' : 'FAIL'} ${route}: ${name}`);
    return result.passed;
  };
  await runSuite(session, {base, revision: target === 'build' ? revision : undefined, output, check});
} catch (error) {
  report.error = session ? session.sanitize(error.message) : error.message;
  console.error(report.error);
} finally {
  report.passed = !report.error && !interrupted && report.checks.length > 0 && report.checks.every(c => c.passed);
  if (session?.id) {
    try {
      const details = await session.executor('getSessionDetails');
      const parsed = typeof details === 'string' ? JSON.parse(details) : details;
      const data = parsed.automation_session || parsed;
      if (data.browser_url) report.sessionUrl = data.browser_url;
      else if (data.build_hashed_id) report.sessionUrl = `https://automate.browserstack.com/builds/${data.build_hashed_id}/sessions/${session.id}`;
      await session.executor('setSessionStatus', {status: report.passed ? 'passed' : 'failed', reason: report.passed ? 'SIMS real-device touch suite passed' : 'SIMS assertion or setup failure; see GitHub test artifacts'});
    } catch (error) { report.reportingError = session.sanitize(error.message); }
  }
  await cleanup(); if (report.cleanupError) report.passed = false;
  report.finished = new Date().toISOString(); await save();
  const failures = report.checks.filter(c => !c.passed).length + (report.error ? 1 : 0);
  const xml = `<?xml version="1.0" encoding="UTF-8"?><testsuite name="SIMS ${device}" tests="${report.checks.length + (report.error ? 1 : 0)}" failures="${failures}">${report.checks.map(c => `<testcase classname="${escape(c.route)}" name="${escape(c.name)}" time="${c.seconds}">${c.passed ? '' : `<failure message="${escape(c.error)}"/>`}</testcase>`).join('')}${report.error ? `<testcase name="setup or suite"><failure message="${escape(report.error)}"/></testcase>` : ''}</testsuite>`;
  await fs.writeFile(path.join(output, 'junit.xml'), xml);
  const summary = `### SIMS ${device}: ${report.passed ? 'passed' : 'failed'}\n\nTarget: ${target}. Commit: \`${revision}\`.\n\n${report.checks.filter(c => c.passed).length}/${report.checks.length} checks passed.\n\n${report.sessionUrl ? `[BrowserStack recording and logs](${report.sessionUrl})\n\n` : ''}${report.error ? `Setup/suite error: ${report.error}\n\n` : ''}Download the device artifact for screenshots, JSON and JUnit results.\n`;
  await fs.writeFile(path.join(output, 'summary.md'), summary);
  if (process.env.GITHUB_STEP_SUMMARY) await fs.appendFile(process.env.GITHUB_STEP_SUMMARY, summary);
  if (!report.passed) process.exitCode = 1;
  console.log(`${device}: ${report.passed ? 'PASS' : 'FAIL'} (${report.checks.length} checks)`);
}
