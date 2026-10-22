/* Offline control/geometry/data harness; does not claim browser rendering. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const base=__dirname,html=fs.readFileSync(path.join(base,'player.html'),'utf8');
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]);assert.equal(scripts.length,2);
const data=JSON.parse(scripts[0]);assert.deepEqual(data,JSON.parse(fs.readFileSync(path.join(base,'animation.json'),'utf8')));new vm.Script(scripts[1]);
let width=380,resize,frames=[],drawCalls=0;
const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:(...args)=>{for(const a of args)if(typeof a==='number')assert(Number.isFinite(a),k);drawCalls++;},set:(o,k,v)=>{o[k]=v;return true;}});
class Element{constructor(){this.value='0';this.textContent='';this.listeners={};this.options=[];}get clientWidth(){return width;}add(o){this.options.push(o);if(this.options.length===1)this.value=String(o.value);}addEventListener(k,f){this.listeners[k]=f;}getContext(){return ctx;}}
const els={};const globals={document:{getElementById:id=>els[id]||(els[id]=new Element()),querySelector:()=>new Element()},Option:class{constructor(label,value){this.label=label;this.value=value;}},ResizeObserver:class{constructor(f){resize=f;}observe(){}},requestAnimationFrame:f=>frames.push(f),atob:s=>Buffer.from(s,'base64').toString('binary'),Uint8Array,DataView,Math,JSON,Number};
els.data=new Element();els.data.textContent=scripts[0];const realm=vm.createContext(globals);vm.runInContext(scripts[1],realm);
function event(id,kind,value){if(value!==undefined)els[id].value=String(value);els[id].listeners[kind]();}
let selections=0;
for(const w of [260,380,650]){width=w;resize();for(let model=1;model<8;model++)for(let c=2;c<8;c++)for(let start=0;start<2;start++)for(let clip=0;clip<2;clip++){
 event('model','change',model);event('eccentric','change',c);event('start','change',start);event('clip','change',clip);
 for(const offset of [0,11.4,22.8]){event('seek','input',offset);assert.equal(els.time.textContent,'Simulation time '+(data.clips[clip].start+offset).toFixed(2)+' s');selections++;}
 assert.equal(els.title2.textContent,'Eccentric · '+data.conditions[c].name);
 if(!clip)assert.equal(els.status0.textContent,'Early response · unclassified');
}}
event('clip','change',0);event('play','click');let f=frames.shift();f(0);f=frames.shift();f(100);assert.equal(els.time.textContent,'Simulation time 0.15 s');event('play','click');const held=els.time.textContent;f=frames.shift();f(200);assert.equal(els.time.textContent,held);
// A stale callback from a paused generation cannot advance a resumed clip.
event('play','click');const stale=frames.shift();event('play','click');event('play','click');stale(500);assert.equal(frames.length,1);frames.shift()(600);event('seek','input',22.79);frames.shift()(700);frames.shift()(800);assert.equal(els.play.textContent,'Play');assert.equal(els.time.textContent,'Simulation time 22.80 s');assert.equal(frames.length,0);
// Byte indexing and interpolation agree with independently read samples.
const raw=Buffer.from(data.values,'base64');assert.equal(raw.length,2*128*229*3*4);
for(const clip of [0,1])for(const caseIndex of [0,1,16,127])for(const j of [0,117,228])for(const channel of [0,1,2]){
 const expected=raw.readFloatLE((((clip*128+caseIndex)*229+j)*3+channel)*4);
 const actual=vm.runInContext(`sample(${clip},${caseIndex},${j}*.1,${channel})`,realm);assert(Math.abs(expected-actual)<1e-12);
}
assert(!html.includes('GUARD_DATA_PLACEHOLDER'));assert(!/fetch\(|XMLHttpRequest|WebSocket/.test(html));
const result={selection_seek_checks:selections,finite_canvas_operations:drawCalls,all_models_eccentricities_starts_clips:true,play_pause_end_and_stale_frame:true,display_bytes_and_indices:true,offline_no_network:true,method:'Offline JavaScript canvas/DOM harness; not a browser rendering test'};
console.log(JSON.stringify(result,null,2));
