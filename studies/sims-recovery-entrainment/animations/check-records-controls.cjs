// Offline DOM/control checks. No browser navigation or local-file URL is used.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const file=require('path').join(__dirname,'source','records-and-memory.html');
const html=fs.readFileSync(file,'utf8'),script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
function run(width=736,{saved=null,failHost=false,reduced=false}={}){
  class Element{
    constructor(tag,attrs={}){this.tag=tag;this.attrs=attrs;this.children=[];this.dataset={};this.style={};this.handlers={};this.textContent='';this.value=attrs.value||'';}
    setAttribute(k,v){this.attrs[k]=String(v);}
    appendChild(n){this.children.push(n);return n;}
    replaceChildren(...n){this.children=n;}
    addEventListener(k,f){this.handlers[k]=f;}
    getBoundingClientRect(){return {width:this.tag==='svg'?(width<640?width:(width-24)/2):width};}
    querySelectorAll(selector){
      const found=[],matches=n=>selector[0]==='['?Object.hasOwn(n.attrs,selector.slice(1,-1)):n.tag===selector;
      const visit=n=>{for(const c of n.children){if(matches(c))found.push(c);visit(c);}};visit(this);return found;
    }
    querySelector(s){return this.querySelectorAll(s)[0]||null;}
    set innerHTML(value){
      this.children=[];const stack=[this],voids=new Set(['input','br','hr']);
      for(const token of value.match(/<[^>]+>|[^<]+/g)||[]){
        if(token.startsWith('</')){stack.pop();continue;}
        if(token.startsWith('<')){
          const m=token.match(/^<(\w+)([\s\S]*?)>$/);if(!m)continue;const attrs={};
          for(const a of m[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g))attrs[a[1]]=a[2]||'';
          const node=new Element(m[1],attrs);stack.at(-1).appendChild(node);if(!voids.has(m[1]))stack.push(node);
        }else stack.at(-1).textContent+=token;
      }
    }
  }
  const root=new Element('div');root.innerHTML=html.slice(html.indexOf('</style>')+8,html.indexOf('<script>'));
  let id=0,time=0,saves=0,lastSaved;const frames=new Map(),wh={},dh={};
  const context={document:{hidden:false,getElementById:()=>root,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),addEventListener:(k,f)=>dh[k]=f},window:{openai:{widgetState:saved,setWidgetState:p=>{saves++;lastSaved=p;if(failHost)throw Error('Optional host unavailable');return Promise.resolve();}},matchMedia:()=>({matches:reduced}),addEventListener:(k,f)=>wh[k]=f},performance:{now:()=>time},requestAnimationFrame:f=>{frames.set(++id,f);return id;},cancelAnimationFrame:i=>frames.delete(i)};
  vm.runInNewContext(script,context,{timeout:2000});
  const el=name=>root.querySelector(`[data-${name}]`),fire=(name,event,value)=>{const n=el(name);if(value!==undefined)n.value=value;n.handlers[event]({target:n});};
  const advance=ms=>{time+=ms;const todo=[...frames.values()];frames.clear();todo.forEach(f=>f(time));};
  const panels=root.querySelectorAll('section');assert.strictEqual(panels.length,4);assert.strictEqual(saves,0);
  assert(panels.every(p=>p.querySelector('svg').children.length>12));
  fire('checkpoint','click');assert.strictEqual(el('time').textContent,'24.0');assert(el('play').textContent.startsWith('Apply resets'));
  const read=(index,owner,key)=>panels[index].querySelectorAll('[data-owner]')[owner].querySelector(`[data-${key}]`).textContent;
  for(let i=0;i<4;i++){assert.strictEqual(read(i,1,'record'),'Flagged');assert.strictEqual(read(i,1,'memory'),'0.37');}
  fire('play','click');
  if(!reduced){
    assert.strictEqual(read(1,1,'record'),'None');assert.strictEqual(read(1,1,'memory'),'0.37');
    assert.strictEqual(read(2,1,'record'),'Flagged');assert.strictEqual(read(2,1,'memory'),'0.50');
    advance(100);assert(Number(el('time').textContent)>24);fire('play','click');assert.strictEqual(frames.size,0);
  }
  fire('time-slider','input','72');fire('time-slider','change');
  assert.strictEqual(read(0,1,'memory'),'0.28');assert.strictEqual(read(1,1,'memory'),'0.86');
  assert.strictEqual(read(2,1,'memory'),'0.31');assert.strictEqual(read(3,1,'memory'),'0.89');
  assert(panels[1].querySelector('[data-choice]').textContent.endsWith('B: Explore'));
  assert(panels[2].querySelector('[data-choice]').textContent.endsWith('B: Familiar'));
  assert.strictEqual(el('play').textContent,'Replay');
  fire('play','click');
  if(reduced)assert.strictEqual(el('time').textContent,'24.0');
  else {for(let i=0;i<85;i++)advance(100);assert.strictEqual(el('time').textContent,'24.0');assert.strictEqual(frames.size,0);}
  assert.strictEqual(read(1,1,'record'),'Flagged','Replay pauses before reset');
  wh['openai:set_globals']({detail:{globals:{widgetState:{privateContent:{id:'records-and-memory',version:1,time:24,applied:true}}}}});
  assert.strictEqual(read(1,1,'record'),'None');assert.strictEqual(read(1,1,'memory'),'0.37');
  assert.strictEqual(read(2,1,'memory'),'0.50');
  fire('time-slider','input','71.99');fire('play','click');if(!reduced)advance(100);
  assert.strictEqual(el('time').textContent,'72.0');assert.strictEqual(frames.size,0);
  assert(Buffer.byteLength(JSON.stringify(lastSaved))<16384);
  return {width,failHost,reduced,initialization:true,checkpointPause:true,isolatedResets:true,seekReplayRestore:true,finitePlayback:true};
}
const checks=[run(736),run(320),run(1024,{failHost:true}),run(360,{reduced:true}),run(736,{saved:{privateContent:{id:'records-and-memory',version:1,time:48,applied:true}}})];
const reportPath=__dirname+'/checks/records-memory.json',report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
report.offlineControls=checks;report.visualInspection='Browser rendering not verified. Offline DOM/control checks are not browser layout checks.';
fs.writeFileSync(reportPath,JSON.stringify(report,null,2));console.log(JSON.stringify(checks,null,2));
