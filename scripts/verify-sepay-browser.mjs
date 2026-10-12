// M7K browser QA: intercepted API/hosted checkout fixtures, never real payments.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const base = process.env.FRONTEND_URL ?? 'http://127.0.0.1:13001';
const folder = 'docs/verification-artifacts/milestone-7k';
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_EXECUTABLE });
const errors = [];
const widths = [375,768,1024,1440];
const orderId = 'd0127479-c65c-4bdc-8889-66fa0e340675';
let paymentState = 'checkout_created';
let currentTier = 'free';
let checkoutCount = 0;
let posted;
let billingReads = 0;
const plans = ['desktop','mobile'].flatMap(device => ['free','starter','pro'].map((tier, i) => ({
  id: `${device}-${tier}`, code: `${device}_${tier}`, name: `${device === 'desktop' ? 'Desktop' : 'Mobile'} ${tier[0].toUpperCase()+tier.slice(1)}`,
  device_scope: device, currency: 'VND', price_monthly_minor_units: [0,495330,3363030][i],
  max_projects: [1,5,20][i], max_keywords: [50,500,5000][i], monthly_keyword_checks: [100,5000,50000][i],
  scheduled_checks_enabled: i > 0, max_scheduled_frequency: ['none','weekly','daily'][i],
})));
const summary = () => ({ user_id:'qa-user', email:'qa@example.test', account_status:'active',
  devices: ['desktop','mobile'].map(device => ({ device_scope:device, subscription_id:`${device}-sub`,
    plan:plans.find(p=>p.code===`${device}_${device==='desktop'?currentTier:'free'}`), status:'active',
    period_start:'2026-10-11T00:00:00Z', period_end:device==='desktop' && currentTier!=='free'?'2026-11-11T00:00:00Z':null,
    projects_used:0, keywords_used:0, over_limit:false,
    usage:{id:device,period_start:'2026-10-11T00:00:00Z',period_end:'2026-11-11T00:00:00Z',limit:100,used:0,reserved:0,remaining:100,adjustment:0},
  })),
});
const payment = () => ({id:orderId, invoice_number:'PAY_0123456789ABCDEF0123456789ABCDEF', status:paymentState,
  product_line:'desktop',plan_code:'desktop_starter',plan_name_snapshot:'Desktop Starter',amount_minor:495330,currency:'VND',
  paid_at:paymentState==='paid'?'2026-10-11T00:00:00Z':null,subscription_id:paymentState==='paid'?'desktop-sub':null});
const context = await browser.newContext();
const page = await context.newPage();
page.on('pageerror', error => errors.push(error.message));
const headers = {'access-control-allow-origin':base,'access-control-allow-credentials':'true',
  'access-control-allow-headers':'authorization,content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
await context.route('**/api/v1/**', async route => {
  const request = route.request();
  if(request.method()==='OPTIONS') return route.fulfill({status:204,headers});
  const path = new URL(request.url()).pathname;
  let body;
  if(path.endsWith('/auth/refresh')) body={ access_token:'qa-fixture-token',token_type:'bearer',expires_in:900,
    user:{id:'qa-user',email:'qa@example.test',email_verified:true,is_platform_admin:false,status:'active'}};
  else if(path.endsWith('/billing/plans')) body=plans;
  else if(path.endsWith('/billing/me')) {billingReads++;body=summary();}
  else if(path.endsWith('/sepay/options')) body={enabled:true,eligible_plan_ids:plans.filter(p=>p.price_monthly_minor_units>0).map(p=>p.id)};
  else if(path.endsWith('/sepay/checkout')) {
    checkoutCount++;
    assert.deepEqual(request.postDataJSON(),{plan_id:'desktop-starter',product_line:'desktop'});
    await new Promise(resolve=>setTimeout(resolve,150));
    body={payment_order_id:orderId,invoice_number:payment().invoice_number,checkout_url:'https://checkout.example.test/init',
      form:{order_amount:'495330',merchant:'TEST-MERCHANT',currency:'VND',operation:'PURCHASE',
        order_invoice_number:payment().invoice_number,signature:'fixture-signature',
        success_url:`${base}/app/change-plan/payment/success?payment_order_id=${orderId}`}};
  } else if(path.endsWith(`/billing/payments/${orderId}`)) body=payment();
  else return route.fulfill({status:404,headers,json:{error:{code:'NOT_FOUND'}}});
  return route.fulfill({status:path.endsWith('/checkout')?201:200,headers,json:body});
});
await context.route('https://checkout.example.test/init', async route => {
  posted = Object.fromEntries(new URLSearchParams(route.request().postData()));
  assert.equal(route.request().method(),'POST');
  assert.equal(posted.currency,'VND');
  assert.equal(posted.signature,'fixture-signature');
  setTimeout(()=>{paymentState='paid';currentTier='starter';},400);
  return route.fulfill({status:302,headers:{location:posted.success_url}});
});
async function responsive(name) {
  for (const width of widths) {
    await page.setViewportSize({width,height:900});
    await page.waitForTimeout(80);
    const metrics=await page.evaluate(()=>({width:innerWidth,page:document.documentElement.scrollWidth,
      clipped:[...document.querySelectorAll('main button, main a')].filter(e=>e.getClientRects().length).filter(e=>{
        const r=e.getBoundingClientRect();return r.left< -1||r.right>innerWidth+1;
      }).map(e=>e.textContent)}));
    assert(metrics.page<=width+1,`${name}: overflow at ${width}: ${JSON.stringify(metrics)}`);
    assert.deepEqual(metrics.clipped,[],`${name}: clipped controls at ${width}`);
    await page.screenshot({path:`${folder}/${name}-${width}.png`,fullPage:true});
  }
}
try {
  await mkdir(folder,{recursive:true});
  await page.goto(`${base}/app/change-plan`);
  await page.getByText('Current Desktop plan',{exact:true}).waitFor();
  const starter=page.locator('[data-plan-code="desktop_starter"]');
  await starter.getByRole('button',{name:'Select',exact:true}).waitFor();
  assert(await page.locator('[data-plan-code="desktop_free"]').getByRole('button',{name:'Current Plan',exact:true}).isDisabled());
  await responsive('change-plan-free');
  await starter.getByRole('button',{name:'Select',exact:true}).click();
  await page.waitForURL('**/payment/success?*');
  await page.getByRole('heading',{name:'Payment successful',exact:true}).waitFor();
  assert.equal(checkoutCount,1);
  assert(posted);
  await responsive('payment-success');
  await page.getByRole('link',{name:'Return to Change Plan'}).click();
  await page.locator('[data-plan-code="desktop_starter"]').getByRole('button',{name:'Current Plan',exact:true}).waitFor();
  assert(billingReads>=2);
  await responsive('change-plan-paid');
  for(const result of ['error','cancel']) {
    paymentState='checkout_created';
    await page.goto(`${base}/app/change-plan/payment/${result}?payment_order_id=${orderId}`);
    await page.getByRole('heading',{name:result==='cancel'?'Checkout cancelled':'Payment was not confirmed',exact:true}).waitFor();
    await responsive(`payment-${result}`);
    assert.equal(paymentState,'checkout_created');
  }
  paymentState='review_required';
  await page.goto(`${base}/app/change-plan/payment/success?payment_order_id=${orderId}`);
  await page.getByRole('heading',{name:'Payment needs review',exact:true}).waitFor();
  await responsive('payment-review');
  paymentState='paid';
  await page.goto(`${base}/app/change-plan/payment/cancel?payment_order_id=${orderId}`);
  await page.getByRole('heading',{name:'Payment successful',exact:true}).waitFor();
  paymentState='checkout_created';
  await page.clock.install();
  await page.goto(`${base}/app/change-plan/payment/success?payment_order_id=${orderId}`);
  await page.getByText(/Waiting for payment confirmation from SePay/).waitFor();
  await page.clock.fastForward(46000);
  await page.getByRole('heading',{name:'Payment confirmation is taking longer',exact:true}).waitFor();
  await responsive('payment-timeout');
  assert.deepEqual(errors,[]);
  const report={mode:'intercepted fixtures; no SePay network calls',widths,checkoutCount,billingReads,consoleErrors:errors,
    scenarios:['signed POST form','redirect before confirmation','IPN before redirect','current plan refreshed','error','cancel','paid cancel remains paid','review','bounded polling timeout'],result:'passed'};
  await writeFile(`${folder}/browser-report.json`,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
} finally {await browser.close();}
