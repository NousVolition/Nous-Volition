const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const file=require('node:path').join(__dirname, '../fragments/sims-claim-testing.html');
const html=fs.readFileSync(file,'utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);assert(!html.includes('\\"'));assert(!/<!doctype|<html|<body|fetch\(/i.test(html));
let width=736,callback=null,saved=null;const winEvents={};
class El{constructor(tag='div'){this.tag=tag;this.children=[];this.attrs={};this.listeners={};this.style={};this.value='';this.checked=false;this.textContent='';}setAttribute(k,v){this.attrs[k]=v;}append(...es){this.children.push(...es);}replaceChildren(...es){this.children=es;}addEventListener(k,f){this.listeners[k]=f;}getBoundingClientRect(){return{width};}}
const els={};for(const[,type,name]of html.matchAll(/data-(control|display|action)="([^"]+)"/g))els[`[data-${type}="${name}"]`]=new El();
const get=(type,name)=>els[`[data-${type}="${name}"]`];
const root={querySelector:s=>{assert(els[s],'Missing element '+s);return els[s];}};
const context={document:{getElementById:id=>{assert.equal(id,'sims-claims-lab');return root;},createElementNS:(_,tag)=>new El(tag),createElement:tag=>new El(tag),addEventListener(){}},window:{openai:{setWidgetState:s=>{saved=s;return Promise.resolve();}},setInterval:f=>{callback=f;return 1;},clearInterval:()=>{callback=null;},matchMedia:()=>({matches:false}),addEventListener:(n,f)=>{winEvents[n]=f;}},ResizeObserver:class{constructor(f){this.f=f;}observe(){this.f();}},console};context.globalThis=context;vm.createContext(context);
vm.runInContext(script.replace(/\}\)\(\);\s*$/,'globalThis.test={predict,act,simulate,preset,normalize,rng,neighbors,weights,newLedger,observe,indexEvidence,phaseState,rows,draw,restore,get:()=>({config,cursor,selected,run,ledgers,timer})};})();'),context);
const t=context.test,plain=x=>JSON.parse(JSON.stringify(x));
const eq=(a,b)=>assert.deepEqual(plain(a),plain(b));
let probabilityChecks=0;
for(const degree of [1,2,8])for(let bits=0;bits<2**degree;bits++)for(const before of[0,1])for(const initial of[0,1])for(const innovation of[0,.02]){
 const ns=Array.from({length:degree},(_,i)=>(bits>>>i)&1),a=ns.filter(x=>x===0).length,ctx={before,initial,neighborStates:ns,innovation};
 const expectedCopy=(1-innovation)*(a/degree*(before===1?.85:1)+(degree-a)/degree*(before===0?.15:0))+innovation*(before===1?1:0);
 assert(Math.abs(t.predict('copy',ctx)-expectedCopy)<1e-12);
 for(const rule of['hold','majority','oppose']){const out=t.act(rule,ctx,()=>{throw Error('deterministic rule consumed randomness');});assert.equal(t.predict(rule,ctx),out===0?1:0);}
 probabilityChecks++;
}
for(const ctx of[{before:0,initial:0,neighborStates:[0,1],innovation:.02},{before:1,initial:1,neighborStates:[0,0],innovation:0},{before:0,initial:1,neighborStates:[1],innovation:.02}]){
 const rand=t.rng(8871),n=60000;let a=0;for(let i=0;i<n;i++)a+=t.act('copy',ctx,rand)===0;assert(Math.abs(a/n-t.predict('copy',ctx))<.008);
}
// Zero-probability contradictions are separate from low likelihood and ambiguous evidence.
let l=t.newLedger();const ambiguous={predictions:[1,1,1,0],observed:0};
l=t.observe(l,ambiguous,0);eq(t.weights(l),[1/3,1/3,1/3,0]);
assert.equal(l.logL[3],-Infinity);
let rare=t.observe(t.newLedger(),{predictions:[.02,1,0,0],observed:0},0);assert(Number.isFinite(rare.logL[0]));assert(t.weights(rare)[0]>0);
let cases=0;
for(const topology of['ring','star'])for(const mode of['network','probe'])for(const preset of['matched','mismatch','mixed'])for(let seed=1;seed<=12;seed++){
 const c={topology,mode,seed,innovation:.02,preset,...t.preset(preset)},r=t.simulate(c),ledgers=t.indexEvidence(r.events);
 assert(r.events.length>0);assert.equal(ledgers.length,r.events.length+1);assert(ledgers[0].every(s=>s.n===0));
 const counts=Array(9).fill(0);let current=r.initial.slice(),lastSec=0;
 r.events.forEach((e,k)=>{
   assert.equal(e.beforeState[e.seat],e.ctx.before);
   eq(e.ctx.neighborStates,e.ctx.neighborIds.map(id=>e.beforeState[id]));
   if(mode==='network'){eq(e.beforeState,current);assert(e.second>=lastSec);lastSec=e.second;}
   current=e.afterState;
   assert.equal(e.afterState[e.seat],e.observed);
   for(let j=0;j<9;j++)if(j!==e.seat)assert.equal(e.beforeState[j],e.afterState[j]);
   for(let j=0;j<4;j++){assert(e.predictions[j]>=0&&e.predictions[j]<=1);assert.equal(e.predictions[j],t.predict(['copy','hold','majority','oppose'][j],e.ctx));}
   assert.equal(e.claimProbability,e.predictions[['copy','hold','majority','oppose'].indexOf(c.claims[e.seat])]);
   const trueProb=e.predictions[['copy','hold','majority','oppose'].indexOf(c.actual[e.seat])];assert((e.observed===0?trueProb:1-trueProb)>0);
   counts[e.seat]++;eq(ledgers[k+1].map(x=>x.n),counts);assert.equal(ledgers[k+1][e.seat].last,k);
   assert(Number.isFinite(ledgers[k+1][e.seat].logL[['copy','hold','majority','oppose'].indexOf(c.actual[e.seat])]));
 });
 if(mode==='probe'){
   assert.equal(r.events.length,topology==='ring'?432:304);
   for(let seat=0;seat<9;seat++){const seen=new Map();for(const e of r.events.filter(e=>e.seat===seat)){const key=e.ctx.before+':'+e.ctx.neighborStates.filter(v=>v===0).length;seen.set(key,(seen.get(key)||0)+1);}assert([...seen.values()].every(n=>n===8));}
 }
 const changedClaims={...c,claims:Array(9).fill('hold')};const alternative=t.simulate(changedClaims);
 eq(alternative.events.map(e=>[e.seat,e.second,e.probeId,e.beforeState,e.afterState]),r.events.map(e=>[e.seat,e.second,e.probeId,e.beforeState,e.afterState]));
 eq(t.simulate(c),r);cases++;
}
// The initial UI has a precommitted prediction but no observed outcome or scored evidence.
assert.equal(t.get().cursor,0);assert(t.phaseState().ledger.every(x=>x.n===0));assert.equal(get('display','outcome').textContent,'Outcome not yet shown');
get('action','step').listeners.click();assert.equal(t.get().cursor,1);assert.equal(t.phaseState().processed,1);assert(get('display','outcome').textContent.startsWith('Actually chose'));
get('action','step').listeners.click();assert.equal(t.get().cursor,2);assert.equal(t.phaseState().processed,1);assert.equal(get('display','outcome').textContent,'Outcome not yet shown');
get('action','finish').listeners.click();assert.equal(t.phaseState().processed,t.get().run.events.length);
t.rows[4].button.listeners.click();assert.equal(t.get().selected,4);assert(get('display','selected-title').textContent.endsWith('4'));
get('action','jump').listeners.click();assert.equal(t.phaseState().event.seat,4);assert(t.phaseState().revealed);
get('control','mode').value='probe';get('control','mode').listeners.change();assert.equal(t.get().config.mode,'probe');assert.equal(t.get().cursor,0);
get('control','topology').value='star';get('control','topology').listeners.change();assert.equal(t.get().run.events.length,304);assert.equal(get('display','network').children.filter(x=>x.tag==='line').length,8);
get('control','claim').value='majority';get('control','claim').listeners.change();assert.equal(t.get().config.claims[4],'majority');assert.equal(t.get().config.preset,'custom');assert.equal(t.phaseState().processed,0);
get('action','play').listeners.click();assert.equal(t.get().timer,1);winEvents['openai:set_globals']({detail:{globals:{widgetState:saved}}});assert.equal(t.get().timer,1);callback();assert.equal(t.get().cursor,1);get('action','play').listeners.click();assert.equal(t.get().timer,null);
const state=plain(saved);state.modelContent.cursor=20;state.modelContent.selected=7;assert(t.restore(state));assert.equal(t.get().cursor,20);assert.equal(t.get().selected,7);
width=320;t.draw();assert.equal(get('display','network').attrs.viewBox,'0 0 320 300');
const demo=t.simulate({seed:20261008,mode:'network',topology:'ring',innovation:.02,...t.preset('mismatch')});const demoEvidence=t.indexEvidence(demo.events).at(-1);
console.log(JSON.stringify({passed:true,probabilityContexts:probabilityChecks,simulationCases:cases,behaviorSamples:180000,checks:['prediction/action separation','claims cannot change actual actions','no future evidence in playback','deterministic replay','controlled context coverage','zero-probability contradictions','ambiguous rules remain tied','all participant evidence counts','preset/custom/inspection/replay controls'],defaultRun:{decisions:demo.events.length,sim0ClaimWeight:t.weights(demoEvidence[0])[0],sim0BestRule:['copy','hold','majority','oppose'][t.weights(demoEvidence[0]).indexOf(Math.max(...t.weights(demoEvidence[0])))]}},null,2));
