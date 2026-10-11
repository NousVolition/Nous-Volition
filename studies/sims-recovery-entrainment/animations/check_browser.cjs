const fs=require('fs'),assert=require('assert'),path=require('path');
const pw=require('playwright');
const base=__dirname;
const names=['two-orbits','within-and-position','moving-with-memory','memory-next-path','memory-journey-cycle'];
(async()=>{
 const browser=await pw.chromium.launch({headless:true,...(process.env.SIMS_BROWSER_EXECUTABLE?{executablePath:process.env.SIMS_BROWSER_EXECUTABLE}:{})});
 const records=[];
 try{
  for(const name of names){
   const page=await browser.newPage({viewport:{width:760,height:900}}),errors=[],network=[];
   page.on('pageerror',error=>errors.push(error.message));
   page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url());});
   await page.addInitScript(()=>{window.animationErrors=[];window.addEventListener('error',e=>window.animationErrors.push(e.message));});
   await page.goto('file:///'+path.join(base,name+'.html').replace(/\\/g,'/'));
   const frame=page.frames().find(f=>f.parentFrame());assert(frame);
   const button=frame.locator('[data-play]');const before=await frame.locator('input[type=range]').inputValue();
   await button.click();await page.waitForTimeout(250);const after=await frame.locator('input[type=range]').inputValue();assert(Number(after)>Number(before));await button.click();
   if(name==='memory-journey-cycle'){
    await frame.locator('input[type=range]').evaluate(el=>{el.value='44';el.dispatchEvent(new Event('input',{bubbles:true}));});
    assert((await frame.locator('.sims-svg').first().getAttribute('aria-label')).includes('Explore → Familiar → Explore'));
   }
   await page.setViewportSize({width:320,height:1100});await page.waitForTimeout(150);
   assert(await frame.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   errors.push(...await frame.evaluate(()=>window.animationErrors));assert.deepStrictEqual(errors,[]);assert.deepStrictEqual(network,[]);
   records.push({name,played:true,narrowLayout:true,errors,networkRequests:network.length});await page.close();
  }
  const page=await browser.newPage({viewport:{width:760,height:900}});
  await page.goto('file:///'+path.join(base,'index.html').replace(/\\/g,'/'));
  const links=await page.locator('a').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
  for(const link of links)assert(fs.existsSync(path.resolve(base,link)));
  await page.screenshot({path:path.join(base,'checks','animation-guide.png')});await page.close();
  fs.writeFileSync(path.join(base,'checks','standalone-exports.json'),JSON.stringify({status:'passed',records,guideLinks:links.length},null,2)+'\n');
  console.log(JSON.stringify({status:'passed',records,guideLinks:links.length},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
