import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
export async function verifyResponsive(page, name) {
 await page.waitForLoadState('networkidle');
 const widths=[375,768,1024,1280,1440];const folder=process.env.SCREENSHOT_DIR ?? 'docs/screenshots/milestone-6.5a';const screenshotWidths=new Set(process.env.SCREENSHOT_DIR ? [375,768,1024,1440] : [375,1440]);await mkdir(folder,{recursive:true});
 for(const width of widths){await page.setViewportSize({width,height:900});await page.waitForTimeout(100);
 const metrics=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth,controls:[...document.querySelectorAll('main input,main select,main textarea,main button')].filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden').map(e=>({label:e.getAttribute('aria-label')||e.textContent||e.name,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right}))}));
 assert(metrics.page<=width+1,`${name} overflow at ${width}: ${metrics.page}`);
 assert(metrics.controls.every(c=>c.left>=-1 && c.right<=width+1),`${name} clipped controls at ${width}: ${JSON.stringify(metrics.controls.filter(c=>c.left< -1||c.right>width+1))}`);
 if(screenshotWidths.has(width))await page.screenshot({path:`${folder}/${name}-${width}.png`,fullPage:true});
 }
 console.log(JSON.stringify({responsive_screen:name,widths,result:'passed'}));
}
