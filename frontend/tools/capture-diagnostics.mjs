import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('..');
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1280,height:900}});
for(const file of process.argv.slice(2)){
 const absolute=path.resolve(root,file), text=await fs.readFile(absolute,'utf8');
 const html='<html><head><meta charset="utf-8"><title>SQLPlay diagnostic evidence</title></head><body style="margin:40px;background:#f7f8fa;color:#172124;font:14px/1.6 system-ui"><h1>SQLPlay · retained diagnostic evidence</h1><p>This is a real browser capture of a command/test transcript. It is not an application UI failure screenshot.</p><h2></h2><pre style="white-space:pre-wrap;word-break:break-word;border:1px solid #ccd4d0;border-left:5px solid #b44838;background:white;padding:24px"></pre></body></html>';
 await page.setContent(html);await page.locator('h2').textContent();await page.locator('h2').evaluate((el,t)=>el.textContent=t,file);await page.locator('pre').evaluate((el,t)=>el.textContent=t,text);
 const target=path.join(root,'bugs',path.basename(file).replace(/\.[^.]+$/,'')+'-diagnostic.png');
 try{await fs.access(target);console.log('Preserved existing screenshot:',target)}catch{await page.screenshot({path:target,fullPage:true});console.log('Captured:',target)}
}
await browser.close();
