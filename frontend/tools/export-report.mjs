// Small renderer for this repository's trusted Markdown report; no remote content.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';
const root=path.resolve('..');
const markdown=await fs.readFile(path.join(root,'FINAL_REPORT.md'),'utf8');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const inline=s=>escape(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2">$1</a>').replace(/\*([^*]+)\*/g,'<em>$1</em>');
let body='',table=false,list=false,pre=false;
for(const line of markdown.split('\n')){
 if(line.startsWith('```')){pre=!pre;body+=pre?'<pre>':'</pre>';continue}
 if(pre){body+=escape(line)+'\n';continue}
 if(table&&!line.startsWith('|')){body+='</tbody></table>';table=false}
 if(list&&!line.startsWith('- ')){body+='</ul>';list=false}
 if(!line.trim())continue;
 const heading=line.match(/^(#{1,3}) (.*)$/);if(heading){body+=`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`;continue}
 const image=line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);if(image){body+=`<figure><img src="${escape(image[2])}" alt="${escape(image[1])}"></figure>`;continue}
 if(line.startsWith('|')){const cells=line.split('|').slice(1,-1).map(s=>s.trim());if(cells.every(c=>/^:?-+:?$/.test(c)))continue;if(!table){body+='<table><thead><tr>'+cells.map(c=>`<th>${inline(c)}</th>`).join('')+'</tr></thead><tbody>';table=true}else body+='<tr>'+cells.map(c=>`<td>${inline(c)}</td>`).join('')+'</tr>';continue}
 if(line.startsWith('- ')){if(!list){body+='<ul>';list=true}body+=`<li>${inline(line.slice(2))}</li>`;continue}
 body+=`<p>${inline(line)}</p>`;
}
if(table)body+='</tbody></table>';if(list)body+='</ul>';
const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>SQLPlay — Final Report</title><style>@page{size:A4;margin:19mm 17mm}body{font:11px/1.65 Arial,sans-serif;color:#20352e;max-width:900px;margin:auto}h1{font-size:32px;line-height:1.15;color:#175d47;border-bottom:3px solid #175d47;padding-bottom:16px}h2{font-size:22px;color:#175d47;margin-top:28px;break-after:avoid}h3{font-size:15px;margin-top:22px;break-after:avoid}p{margin:10px 0}a{color:#175d47;text-decoration:underline;overflow-wrap:anywhere}code{font-size:10px;background:#edf3ee;padding:2px 4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #d6e3d9;padding:12px}table{width:100%;border-collapse:collapse;font-size:10px;margin:18px 0}th,td{border:1px solid #d5dfd8;padding:7px;text-align:left}th{background:#edf3ee}tr{break-inside:avoid}figure{margin:20px 0 8px;break-inside:avoid;break-after:avoid}img{max-width:100%;max-height:165mm;display:block;object-fit:contain;object-position:left;border:1px solid #d5dfd8}figure+p{font-size:10px;color:#53665b;break-before:avoid}h2:not(:first-of-type){break-before:page}</style></head><body>${body}</body></html>`;
await fs.writeFile(path.join(root,'FINAL_REPORT.html'),html);
const browser=await chromium.launch({channel:'chrome'});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(pathToFileURL(path.join(root,'FINAL_REPORT.html')).href);await page.evaluate(()=>document.fonts.ready);const broken=await page.locator('img').evaluateAll(imgs=>imgs.filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src));if(broken.length||errors.length){await page.screenshot({path:path.join(root,'bugs',`${Date.now()}-report-render-failure.png`),fullPage:true});throw new Error(JSON.stringify({broken,errors}))}
await page.pdf({path:path.join(root,'FINAL_REPORT.pdf'),printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font:9px Arial;width:100%;margin:0 17mm;color:#58675f">SQLPlay · Verified build report · 19 November 2026 <span style="float:right"><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',preferCSSPageSize:true});
console.log(`Exported FINAL_REPORT.pdf with ${await page.locator('img').count()} verified image embeds and no broken images.`);await browser.close();
