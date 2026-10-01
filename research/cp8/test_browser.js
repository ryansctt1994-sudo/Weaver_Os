const {chromium}=require('playwright'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']}),page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+path.resolve('lab.html'));await page.waitForTimeout(300);
 assert.equal(await page.locator('#hudVerify').textContent(),'PASS');
 await page.locator('#demoBtn').click();await page.waitForTimeout(2200);
 assert.equal(await page.locator('#hudVerify').textContent(),'PASS');
 const before=await page.locator('#currentState').textContent();
 await page.locator('#importFile').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schema:'asin-hhc.cp8.snake-proof.v1.1',dimension:3,path_decimal:[0,1,3,2]}))});
 await page.waitForTimeout(200);assert.equal(await page.locator('#currentState').textContent(),before);
 await page.locator('#budgetSelect').selectOption('3000');await page.locator('#searchBtn').click();
 await page.waitForFunction(()=>document.querySelector('#hudStatus').textContent==='COMPLETE');
 assert.equal(await page.locator('#hudVerify').textContent(),'PASS');assert.equal(errors.length,0,errors.join('\n'));
 await browser.close();console.log('Browser checks PASS: load, demo, rejected import preservation, worker search');
})().catch(e=>{console.error(e);process.exit(1)});
