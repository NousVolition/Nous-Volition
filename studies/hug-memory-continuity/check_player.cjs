// Offline DOM/canvas logic checks. This is not a browser layout/accessibility test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let strokes=0,raf;
const ctx=new Proxy({}, {get:(o,k)=>k in o?o[k]:(...args)=>{for(const a of args)if(typeof a==='number')assert(Number.isFinite(a),`nonfinite canvas ${k}`);if(k==='stroke')strokes++;},set:(o,k,v)=>(o[k]=v,true)});
class Element {
  constructor(){this.value='0';this.textContent='';this.style={};this.children=[];this.events={};this.selectors={};}
  add(option){this.children.push(option);}
  append(el){this.children.push(el);}
  querySelector(sel){return this.selectors[sel]??=new Element();}
  getContext(){return ctx;}
  addEventListener(name,fn){this.events[name]=fn;}
}
const ids=Object.fromEntries(['scenario','history','clip','seek','play','clock','clipnote','cards','resetlegend'].map(x=>[x,new Element()]));
const sandbox={console,Uint8Array,Float32Array,Math,Option:function(label,value){this.label=label;this.value=value;},atob:s=>Buffer.from(s,'base64').toString('binary'),document:{getElementById:id=>{assert(id in ids,id);return ids[id];},createElement:()=>new Element()},requestAnimationFrame:fn=>raf=fn,window:{}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname,'animation-data.js'),'utf8'),sandbox);
const html=fs.readFileSync(path.join(__dirname,'player.html'),'utf8');
assert(!/\bfetch\s*\(|XMLHttpRequest|https?:\/\//.test(html),'player must be offline');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];assert.equal(scripts.length,1);
vm.runInContext(scripts[0][1],sandbox);
const api=sandbox.window.hugPlayer,D=api.data;
assert.equal(D.shape[0],1208);assert.equal(D.shape[1],54);
assert.equal(ids.scenario.children.length,9);assert.equal(ids.clip.children.length,8);assert.equal(ids.cards.children.length,3);
for(const [key,x] of Object.entries(api.decoded)){
  assert([...x].every(Number.isFinite),key);
  assert.equal(x.length,D.shape[0]*(key==='A'||key==='S'?9:54),key);
}
let states=0;
for(let s=0;s<9;s++)for(let h=0;h<2;h++)for(let c=0;c<8;c++)for(const f of [0,75,150]){
  ids.scenario.value=String(s);ids.history.value=String(h);ids.clip.value=String(c);ids.seek.value=String(f);api.render();states++;
  assert(ids.clock.textContent.includes(D.times[D.clips[c].start+f].toFixed(1)));
  const statuses=ids.cards.children.map(el=>el.querySelector('.status').textContent);
  assert(!statuses[0].includes('repeat confirmed'));
  const time=D.times[D.clips[c].start+f];
  if(D.scenarios[s].pause&&time>=480&&time<720)assert(statuses.every(x=>x.startsWith('Drive off')));
  if(D.scenarios[s].pause&&time>=720&&time<783)assert(statuses.slice(1).every(x=>x.startsWith('Assessing')));
  if(s===2&&time>=720&&time<750)assert(statuses.every(x=>!x.startsWith('Assessing')));
  assert.equal(ids.resetlegend.style.visibility,s===0?'visible':'hidden');
}
ids.scenario.value='0';ids.history.value='0';ids.clip.value='2';ids.seek.value='75';api.render();
assert(ids.cards.children.every(x=>x.querySelector('.stored').textContent.endsWith('3.000')));
ids.scenario.value='1';ids.clip.value='3';ids.seek.value='0';api.render();
assert(ids.cards.children.every(x=>x.querySelector('.stored').textContent.endsWith('0.000')));
ids.clip.value='0';ids.seek.value='150';api.setPlaying(true);raf(1000);raf(1066);assert.equal(Number(ids.clip.value),1);assert.equal(Number(ids.seek.value),0);
api.setPlaying(false);assert.equal(ids.play.textContent,'Play');
ids.clip.value='7';ids.seek.value='50';ids.clip.events.input();assert.equal(Number(ids.seek.value),0);
console.log(JSON.stringify({passed:true,states_exercised:states,canvas_strokes:strokes,checks:'decoded arrays, finite drawing coordinates, labels, selections, clock, clip transitions and controls',limitation:'offline logic harness, not browser visual QA'},null,2));
