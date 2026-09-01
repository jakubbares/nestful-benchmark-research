import puppeteer from '/opt/homebrew/lib/node_modules/@mermaid-js/mermaid-cli/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser=await puppeteer.launch({executablePath:CHROME,headless:'new',args:['--no-sandbox','--allow-file-access-from-files']});
const page=await browser.newPage();
await page.setViewport({width:1600,height:1000});
const errs=[];
page.on('pageerror',e=>errs.push('PAGEERROR: '+e.message));
page.on('console',m=>{ if(m.type()==='error') errs.push('CONSOLE: '+m.text()); });
await page.goto('file://'+process.cwd()+'/nestful_explorer.html',{waitUntil:'networkidle0'});
await page.waitForFunction(()=>document.getElementById('boot').style.display==='none',{timeout:30000});

const shot=async(n)=>{ await new Promise(r=>setTimeout(r,400)); await page.screenshot({path:`shot_${n}.png`}); };

console.log('shown:', await page.$eval('#nshown',e=>e.textContent));
console.log('items:', await page.$$eval('#list .item',e=>e.length));
console.log('detail h2:', await page.$eval('#detail h2',e=>e.textContent.trim().slice(0,80)));
await shot('01-explorer');

// open the prompt modal
await page.evaluate(()=>document.querySelector('#detail .card button.iconbtn[onclick^="showPrompt"]').click());
await new Promise(r=>setTimeout(r,300));
console.log('modal title:', await page.$eval('#modaltitle',e=>e.textContent.replace(/\s+/g,' ').trim()));
await shot('02-prompt');
await page.evaluate(()=>document.getElementById('modalclose').click());

for (const t of ['compare','overview','prompts','about']){
  await page.evaluate(v=>document.querySelector(`#tabs button[data-v="${v}"]`).click(), t);
  await new Promise(r=>setTimeout(r,350));
  const txt=await page.$eval('#v-'+t,e=>e.innerText.replace(/\s+/g,' ').trim().slice(0,120));
  console.log(t+':', txt);
  await shot('0'+({compare:3,overview:4,prompts:5,about:6}[t])+'-'+t);
}
// exercise filters
await page.evaluate(()=>document.querySelector('#tabs button[data-v="explorer"]').click());
await page.evaluate(()=>{ const q=document.getElementById('q'); q.value='cylinder'; q.dispatchEvent(new Event('input')); });
await new Promise(r=>setTimeout(r,300));
console.log('search "cylinder":', await page.$eval('#nshown',e=>e.textContent));
await page.evaluate(()=>{ document.getElementById('q').value=''; document.getElementById('q').dispatchEvent(new Event('input'));
  document.getElementById('fdiag').value='alt_win'; document.getElementById('fdiag').dispatchEvent(new Event('change')); });
await new Promise(r=>setTimeout(r,300));
console.log('alt_win only:', await page.$eval('#nshown',e=>e.textContent));
await page.evaluate(()=>{ const l=document.querySelector('#list .item'); if(l) l.click(); });
await new Promise(r=>setTimeout(r,300));
await shot('07-altwin');

console.log(errs.length?('ERRORS:\n'+errs.join('\n')):'NO JS ERRORS');
await browser.close();
