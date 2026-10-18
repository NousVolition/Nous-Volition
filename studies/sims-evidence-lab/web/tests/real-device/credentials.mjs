export function credentials(env = process.env) {
  for (const name of ['BROWSERSTACK_USERNAME', 'BROWSERSTACK_ACCESS_KEY']) {
    if (!env[name]?.trim()) throw new Error(`Missing ${name}. Add it as a repository Actions secret; physical tests cannot run without BrowserStack credentials.`);
  }
  return {user: env.BROWSERSTACK_USERNAME, key: env.BROWSERSTACK_ACCESS_KEY};
}

if (process.argv[1]?.endsWith('/credentials.mjs') || process.argv[1]?.endsWith('\\credentials.mjs')) {
  try { credentials(); console.log('BrowserStack credentials are configured.'); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
