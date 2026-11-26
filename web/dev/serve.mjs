// Local-only dev server: serves web/ static files and runs the real Function handler in-process.
// Not part of the publication package (prepare_site uses web/dist + web/functions).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

globalThis.Deno = { env: { get: (name) => process.env[name] } };
const { handler } = await import('../functions/app/handler.ts');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml' };

http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname.startsWith('/functions/v1/app')) {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const request = new Request('http://127.0.0.1' + url.pathname, {
      method: req.method,
      headers: { 'content-type': req.headers['content-type'] || 'application/json', 'x-forwarded-for': req.socket.remoteAddress || 'anon' },
      body: chunks.length ? Buffer.concat(chunks) : undefined,
    });
    const response = await handler(request);
    res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    res.end(Buffer.from(await response.arrayBuffer()));
    return;
  }
  const rel = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/+/, '');
  const file = path.join(root, rel);
  if (!file.startsWith(root) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('not found');
    return;
  }
  res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(8510, '127.0.0.1', () => console.log('web dev server on http://127.0.0.1:8510'));