const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path').join(__dirname, '../fragments/sims-network.html');
const html = fs.readFileSync(path, 'utf8');
assert(!html.includes('\\"'));
assert(!/<!doctype|<html|<body|fetch\(/i.test(html));
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
class El {
  constructor(tag='div') { this.tag=tag; this.children=[]; this.attrs={}; this.listeners={}; this.value=''; this.checked=false; this.textContent=''; }
  setAttribute(k,v) { this.attrs[k]=v; }
  append(el) { this.children.push(el); }
  replaceChildren(...els) { this.children=els; }
  getBoundingClientRect() { return {width:width}; }
  addEventListener(k,fn) { this.listeners[k]=fn; }
}
let width=736;
const els={};
for(const [,type,name] of html.matchAll(/data-(control|display|action)="([^"]+)"/g)) els[`[data-${type}="${name}"]`]=new El();
els['.sim-stage']=new El();
const get=(type,name)=>els[`[data-${type}="${name}"]`];
get('control','topology').value='ring';
get('control','resistance').value='ordinary:0';
get('control','seed').value='20261008';
const root={querySelector:s=>{assert(els[s],`Missing queried element ${s}`);return els[s];}};
let callback=null, saved=null;
const windowListeners={};
const context={document:{getElementById:id=>{assert.equal(id,'sims-network-lab');return root;},createElementNS:(_,tag)=>new El(tag),addEventListener(){}},window:{openai:{setWidgetState:s=>{saved=s;return Promise.resolve();}},setInterval:fn=>{callback=fn;return 1;},clearInterval:()=>{callback=null;},matchMedia:()=>({matches:false}),addEventListener:(name,fn)=>windowListeners[name]=fn},ResizeObserver:class {constructor(fn){this.fn=fn;}observe(){this.fn();}},console};
context.globalThis=context;
vm.createContext(context);
vm.runInContext(script.replace(/\}\)\(\);\s*$/, 'globalThis.testing={simulate,neighborsFor,unanimous,getState:()=>({config,trace,time,timer}),draw};})();'),context);
const t=context.testing;
let cases=0, absorption=0;
for(const topology of ['ring','star']) for(const policy of ['ordinary','hold','oppose']) for(const seat of [0,1]) for(let seed=1;seed<=80;seed++){
 const c={topology,policy,seat,seed,innovation:0};
 const frames=t.simulate(c);
 assert.equal(frames.length,121);
 const initial=frames[0].state;
 let priorBreaks=0, observedFirst=t.unanimous(initial)?0:null, observedBreaks=0;
 const replay=[...initial];
 for(let sec=0;sec<frames.length;sec++){
   const f=frames[sec];
   assert.equal(f.state.length,9);
   assert(f.state.every(x=>x===0||x===1));
   if(policy==='hold')assert.equal(f.state[seat],initial[seat]);
   assert(f.breaks>=priorBreaks);priorBreaks=f.breaks;
   for(const e of f.events){
     assert.equal(e.before,replay[e.seat]);
     const was=t.unanimous(replay), neigh=t.neighborsFor(topology)[e.seat];
     if(policy==='oppose' && e.seat===seat){
       const a=neigh.filter(n=>replay[n]===0).length,b=neigh.length-a;
       assert.equal(e.after,a>b?1:b>a?0:e.before);
     }
     if(e.reason==='copy'){
       assert(neigh.includes(e.donor));
       assert.equal(e.target,replay[e.donor]);
       assert.equal(e.after,e.refused?e.before:e.target);
     }
     replay[e.seat]=e.after;
     const now=t.unanimous(replay);
     if(was&&!now)observedBreaks++;
     if(now&&observedFirst===null)observedFirst=sec;
   }
   assert.equal(JSON.stringify(replay),JSON.stringify(f.state));
   assert.equal(observedBreaks,f.breaks);assert.equal(observedFirst,f.first);
   if(policy==='ordinary' && f.first!==null){assert(t.unanimous(f.state));assert.equal(f.breaks,0);absorption++;}
 }
 assert.equal(JSON.stringify(frames),JSON.stringify(t.simulate(c)));
 cases++;
}
assert(absorption>0);
assert.equal(get('display','network').children.filter(e=>e.tag==='line').length,9);
get('action','step').listeners.click();assert.equal(t.getState().time,1);assert.equal(saved.modelContent.time,1);
get('control','topology').value='star';get('control','topology').listeners.change();
assert.equal(t.getState().time,0);assert.equal(t.getState().config.topology,'star');
assert.equal(get('display','network').children.filter(e=>e.tag==='line').length,8);
get('control','resistance').value='hold:0';get('control','resistance').listeners.change();
assert(t.getState().trace.every(f=>f.state[0]===t.getState().trace[0].state[0]));
get('control','initiative').checked=true;get('control','initiative').listeners.change();assert.equal(t.getState().config.innovation,.02);
get('action','play').listeners.click();assert.equal(t.getState().timer,1);
windowListeners['openai:set_globals']({detail:{globals:{widgetState:saved}}});assert.equal(t.getState().timer,1,'own save echoes must not pause playback');
for(let i=0;i<120;i++)callback();assert.equal(t.getState().time,120);assert.equal(t.getState().timer,null);assert.equal(get('action','play').textContent,'Replay');
get('control','time').value='17';get('control','time').listeners.input();assert.equal(t.getState().time,17);
get('action','new').listeners.click();assert.equal(t.getState().config.seed,20261009);assert.equal(t.getState().time,0);
width=320;t.draw();assert.equal(get('display','network').attrs.viewBox,'0 0 320 330');
console.log(JSON.stringify({passed:true,modelCases:cases,checks:['deterministic replay','binary choices','holder invariant','opponent majority/tie rule','copy/refusal neighbor causality','first agreement and break counting','ordinary consensus absorption','ring/star edges','play and finite replay','step/scrub/new-trial controls','state echo handling','responsive SVG dimensions']},null,2));
