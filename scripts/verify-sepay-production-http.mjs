// Public, unauthenticated release smoke: creates no orders and sends no gateway calls.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
const api = 'https://api.serpsaas.com';
const app = 'https://app.serpsaas.com';
const checks = [];
const backendOnly = process.argv.includes('--backend-only');
async function check(name, url, options = {}, expected = 200, code) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(30_000) });
  assert.equal(response.status, expected, `${name}: HTTP ${response.status}`);
  const type = response.headers.get('content-type') ?? '';
  let data;
  if (type.includes('json')) data = await response.json();
  if (code) assert.equal(data?.error?.code, code, name);
  checks.push({ name, status: response.status, error_code: code ?? null });
  return { response, data };
}
await check('API health', `${api}/health`);
await check('API database health', `${api}/health/db`);
const schema = await check('M7K OpenAPI', `${api}/openapi.json`);
for (const path of ['/api/v1/billing/payments/sepay/checkout','/api/v1/billing/payments/sepay/options','/api/v1/billing/payments/sepay/ipn','/api/v1/billing/payments/{payment_order_id}']) {
  assert(schema.data.paths[path], `Missing ${path}`);
}
await check('IPN publicly reachable and rejects missing provider key', `${api}/api/v1/billing/payments/sepay/ipn`, {
  method: 'POST', headers: {'Content-Type':'application/json'}, body:'{}',
}, 401, 'PAYMENT_PROVIDER_AUTH_FAILED');
await check('Checkout requires user authentication', `${api}/api/v1/billing/payments/sepay/checkout`, {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({plan_id:'00000000-0000-0000-0000-000000000000',product_line:'desktop'}),
}, 401, 'AUTHENTICATION_REQUIRED');
await check('Payment options require authentication', `${api}/api/v1/billing/payments/sepay/options`, {}, 401, 'AUTHENTICATION_REQUIRED');
await check('Payment status requires authentication', `${api}/api/v1/billing/payments/00000000-0000-0000-0000-000000000000`, {}, 401, 'AUTHENTICATION_REQUIRED');
const catalog = await check('VND catalog', `${api}/api/v1/billing/plans`);
assert(catalog.data.length >= 6 && catalog.data.every(plan=>plan.currency==='VND'));
if (!backendOnly) for(const route of ['change-plan','change-plan/payment/success','change-plan/payment/error','change-plan/payment/cancel']) {
  const { response } = await check(`App ${route}`, `${app}/app/${route}`);
  assert.equal(response.headers.get('x-robots-tag'),'noindex, nofollow');
}
if (!backendOnly) await check('Existing public site', 'https://serpsaas.com/');
const report={date:'2026-10-12',mode:'public unauthenticated smoke; no orders, accounts or gateway transactions',checks,passed:checks.length,
  merchant_secret_binding:'requires authenticated Cloud Shell execution',sandbox_e2e:'not performed'};
await mkdir('docs/verification-artifacts/milestone-7k',{recursive:true});
await writeFile(`docs/verification-artifacts/milestone-7k/production-${backendOnly ? 'backend-' : ''}http.json`,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
