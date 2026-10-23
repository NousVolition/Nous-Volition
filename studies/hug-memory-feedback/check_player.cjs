// Offline UI logic and finite-coordinate checks; not a browser layout test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let strokes=0,raf;
const ctx=new Proxy({}, {get:(o,k)=>k in o?o[k]:(...args)=>{for(const a of args)if(typeof a==='number')assert(Number.isFinite(a),`nonfinite canvas ${k}`);if(k==='stroke')strokes++;},set:(o,k,v)=>(o[k]=v,true)});
class Element {
 constructor(){this.value='0';this.textContent='';this.style={};this.children=[];this.events={};this.selectors={};}
 add(x){this.children.push(x);}append(x){this.children.push(x);}querySelector(s){return this.selectors[s]??=new Element();}getContext(){return ctx;}addEventListener(n,fn){this.events[n]=fn;}
}
const names=['view','history','clip','seek','play','clock','clipnote','cards','lowlabel','highlabel','gradient','scale'];const ids=Object.fromEntries(names.map(n=>[n,new Element()]));
const sandbox={console,Uint8Array,Float32Array,Math,Option:function(label,value){this.label=label;this.value=value;},atob:s=>Buffer.from(s,'base64').toString('binary'),document:{getElementById:id=>{assert(id in ids,id);return ids[id];},createElement:()=>new Element()},requestAnimationFrame:fn=>raf=fn,window:{}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path.join(__dirname,'animation-data.js'),'utf8'),sandbox);
const html=fs.readFileSync(path.join(__dirname,'player.html'),'utf8');assert(!/\bfetch\s*\(|XMLHttpRequest|https?:\/\//.test(html),'offline player');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];assert.equal(scripts.length,1);vm.runInContext(scripts[0][1],sandbox);
const api=sandbox.window.hugPlayer,D=api.data;assert.equal(D.frames,906);assert.equal(D.cells,32);assert.equal(ids.clip.children.length,6);assert.equal(ids.cards.children.length,3);
const widths={Q:12,OLD:6*32,DELTA:6*32,AMP:6,A:1,REP:6};for(const [key,x] of Object.entries(api.decoded)){assert.equal(x.length,D.frames*widths[key],key);assert([...x].every(Number.isFinite),key);}
for(let frame=0;frame<D.frames;frame++)for(let j=0;j<6;j++){let total=0;for(let n=0;n<32;n++)total+=api.decoded.DELTA[(frame*6+j)*32+n];assert(Math.abs(total/32)<2e-12,'redistribution retains the mean');}
let states=0;
for(let view=0;view<2;view++)for(let h=0;h<2;h++)for(let c=0;c<6;c++)for(const f of [0,75,150]){
 ids.view.value=String(view);ids.history.value=String(h);ids.clip.value=String(c);ids.seek.value=String(f);api.render();states++;
 const time=D.times[D.clips[c].start+f];assert(ids.clock.textContent.includes(time.toFixed(1)));
 const status=ids.cards.children.map(el=>el.querySelector('.status').textContent);assert(!status[0].includes('repeat confirmed'));
 if(time>=480&&time<720)assert(status.every(x=>x.startsWith('Drive off')));
 if((time>=720&&time<783)||(time>=950&&time<1033))assert(status.slice(1).every(x=>x.startsWith('Assessing')));
 if(view===0)assert(ids.scale.textContent.includes('millionths'));else assert(ids.scale.textContent.includes('synthetic field units'));
 assert(ids.cards.children.every(x=>x.querySelector('.stored').textContent.endsWith('no reset')));
}
ids.clip.value='2';ids.seek.value='0';api.render();assert(ids.cards.children.every(x=>x.querySelector('.stored').textContent.includes('3.000')));
ids.clip.value='0';ids.seek.value='150';api.setPlaying(true);raf(1000);raf(1066);assert.equal(Number(ids.clip.value),1);assert.equal(Number(ids.seek.value),0);api.setPlaying(false);assert.equal(ids.play.textContent,'Play');
ids.clip.value='5';ids.seek.value='40';ids.clip.events.input();assert.equal(Number(ids.seek.value),0);
console.log(JSON.stringify({passed:true,states_exercised:states,canvas_strokes:strokes,checks:'decoded data, conservation of displayed differences, finite drawing, view/clip/history controls, statuses and clock',limitation:'offline logic harness, no browser layout check'},null,2));
