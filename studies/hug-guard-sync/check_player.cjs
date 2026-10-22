/* Offline data, canvas geometry and control checks; not browser rendering. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'player.html'),'utf8'),scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]);assert.equal(scripts.length,2);
const D=JSON.parse(scripts[0]);assert.deepEqual(D,JSON.parse(fs.readFileSync(path.join(__dirname,'animation.json'),'utf8')));new vm.Script(scripts[1]);let width=420,resize,frames=[],draws=0;
const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:(...args)=>{for(const a of args)if(typeof a==='number')assert(Number.isFinite(a),k);draws++;},set:(o,k,v)=>{o[k]=v;return true;}});
class El{constructor(){this.value='0';this.textContent='';this.style={};this.listeners={};this.options=[];}get clientWidth(){return width;}add(o){this.options.push(o);if(this.options.length===1)this.value=String(o.value);}addEventListener(k,f){this.listeners[k]=f;}getContext(){return ctx;}}
const els={data:new El()};els.data.textContent=scripts[0];const realm=vm.createContext({document:{getElementById:id=>els[id]||(els[id]=new El()),querySelector:()=>new El()},Option:class{constructor(label,value){this.label=label;this.value=value;}},ResizeObserver:class{constructor(f){resize=f;}observe(){}},requestAnimationFrame:f=>frames.push(f),atob:s=>Buffer.from(s,'base64').toString('binary'),Uint8Array,DataView,Math,JSON,Number});vm.runInContext(scripts[1],realm);
function event(id,k,v){if(v!==undefined)els[id].value=String(v);els[id].listeners[k]();}
let count=0;
for(const w of [260,420,650]){width=w;resize();for(let condition=2;condition<=7;condition++)for(let arm=0;arm<3;arm++)for(let history=0;history<2;history++)for(let clip=0;clip<D.clips.length;clip++){
 event('condition','change',condition);event('arm','change',arm);event('history','change',history);event('clip','change',clip);
 for(const t of [0,D.duration_s/2,D.duration_s]){event('seek','input',t);assert.equal(els.time.textContent,'Elapsed '+(D.clips[clip].start_s+t).toFixed(2)+' s');count++;}
 assert.equal(els.title2.textContent,'Old · '+D.conditions[condition-1].name);
}}
event('arm','change',0);event('clip','change',0);event('play','click');frames.shift()(0);frames.shift()(100);assert.equal(els.time.textContent,'Elapsed '+(D.clips[0].start_s+.15).toFixed(2)+' s');event('play','click');const held=els.time.textContent;frames.shift()(200);assert.equal(els.time.textContent,held);
event('play','click');const stale=frames.shift();event('play','click');event('play','click');stale(500);assert.equal(frames.length,1);frames.shift()(600);event('seek','input',D.duration_s-.01);frames.shift()(700);frames.shift()(800);assert.equal(els.play.textContent,'Play');assert.equal(frames.length,0);
for(const t of [171,741])assert.equal(vm.runInContext(`assessment(1,3,${t}).status`,realm),'assessing');
for(let model=0;model<2;model++)for(let c=1;c<8;c++){
 const a=D.timelines[(model*3)*7+c-1];const passing=a.time.filter((t,i)=>t>=741&&a.status[i]==='synchronized');if(passing.length)assert.equal(vm.runInContext(`assessment(${model},${c},${passing.at(-1)}).status`,realm),'synchronized');
}
const bytes=Buffer.from(D.values,'base64');assert.equal(bytes.length,D.shape.reduce((a,b)=>a*b,1)*4);
for(const clip of [0,D.clips.length-1])for(const c of [0,41,42,83])for(const sample of [0,57,285]){
 const t=D.clips[clip].sample_start_s+sample*.1,actual=vm.runInContext(`sample(${clip},${c},${t})`,realm),expected=bytes.readFloatLE(((clip*84+c)*286+sample)*4);assert(Math.abs(actual-expected)<1e-10);
}
assert(!html.includes('SYNC_GUARD_DATA_PLACEHOLDER'));assert(!/fetch\(|XMLHttpRequest|WebSocket/.test(html));
console.log(JSON.stringify({selection_seek_checks:count,finite_draw_operations:draws,switch_timestamp_uses_new_stage:true,all_conditions_histories_arms:true,play_pause_end_stale_frames:true,display_byte_indices:true,offline_no_network:true,method:'Offline DOM/canvas harness, not browser rendering'},null,2));
