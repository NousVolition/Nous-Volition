import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';

export const pages = ['index.html', 'latest-run.html', 'sims-repeated-rounds.html',
  'sims-evidence-and-response.html', 'sims-claim-testing.html', 'sims-network.html'];

export async function serveBuild(dist, revision, port = 8000) {
  if (!/^[\w.-]+$/.test(revision)) throw new Error('Invalid build revision');
  const documents = new Map(await Promise.all(pages.map(async file => {
    const html = await fs.readFile(path.join(dist, file), 'utf8');
    return [file, html.replace('<head>', `<head><meta name="sims-ci-revision" content="${revision}">`)];
  })));
  const server = http.createServer((req, res) => {
    const name = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
    const file = name.includes('.') ? name : name + '.html';
    if (!['GET', 'HEAD'].includes(req.method) || !documents.has(file)) { res.writeHead(404).end('Not found'); return; }
    res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'});
    res.end(req.method === 'HEAD' ? undefined : documents.get(file));
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  return server;
}
