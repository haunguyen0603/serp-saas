import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const checks = [];
for (const [url, status, location] of [
  ['http://serpsaas.com/', 301, 'https://serpsaas.com/'],
  ['https://www.serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa', 301, 'https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa'],
  ['https://app.serpsaas.com/blog', 307, 'https://serpsaas.com/blog'],
  ['https://serpsaas.com/login', 307, 'https://app.serpsaas.com/login'],
]) {
  const response = await fetch(url, { redirect: 'manual', signal: AbortSignal.timeout(30000) });
  assert.equal(response.status, status, url);
  const rawLocation = response.headers.get('location');
  // An explicit HTTPS default port is the same URL, e.g. :443 normalizes away.
  assert.equal(new URL(rawLocation, url).href, new URL(location).href, url);
  checks.push({url, status: response.status, rawLocation, normalizedLocation: new URL(rawLocation, url).href});
}
const robots = await fetch('https://app.serpsaas.com/robots.txt', {signal: AbortSignal.timeout(30000)});
assert.equal(robots.status, 200);
assert((await robots.text()).includes('Disallow: /'));
checks.push({url:'https://app.serpsaas.com/robots.txt',status:200,disallowAll:true});
const url='https://serpsaas.com/_next/image?url=%2Fapple-icon.png&w=32&q=75';
const image=await fetch(url,{signal:AbortSignal.timeout(30000)});
assert.equal(image.status,200);
assert.equal(image.headers.get('content-type'),'image/png');
checks.push({url,status:200,contentType:'image/png',bytes:(await image.arrayBuffer()).byteLength});
await fs.writeFile('.tools/m7l-final-release/docs/verification-artifacts/milestone-7l-deployment/production-extra-smoke.json',JSON.stringify({checkedAt:new Date().toISOString(),checks},null,2));
console.log(JSON.stringify({passed:checks.length}));
