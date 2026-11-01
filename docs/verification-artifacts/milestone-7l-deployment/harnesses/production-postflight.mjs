import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const directory = path.resolve('.tools/m7l-final-release/docs/verification-artifacts/milestone-7l-deployment');
const urls = ['https://serpsaas.com/', 'https://serpsaas.com/sitemap.xml', 'https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa', 'https://app.serpsaas.com/app/ranking-alerts', 'https://api.serpsaas.com/health', 'https://api.serpsaas.com/health/db'];
const results = [];
for (const url of urls) {
  const response = await fetch(url, { signal: AbortSignal.timeout(30000), headers: { 'Cache-Control': 'no-cache' } });
  const text = await response.text();
  assert.equal(response.status, 200, url);
  if (url.includes('/health')) assert.equal(JSON.parse(text).status, 'ok');
  if (url.endsWith('/sitemap.xml')) assert.equal((text.match(/<loc>/g) ?? []).length, 27);
  const buildId = text.match(/\\"b\\":\\"([^"\\]+)\\"/)?.[1] ?? null;
  results.push({ url, status: response.status, bytes: Buffer.byteLength(text), buildId, etag: response.headers.get('etag') });
}
await fs.writeFile(path.join(directory, 'after-http.json'), JSON.stringify({ checkedAt: new Date().toISOString(), results }, null, 2));
console.log(JSON.stringify(results, null, 2));
