// Offline DOM/control checks, not browser layout verification.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const file=require('path').join(__dirname,'source','records-recreated.html');
const html=fs.readFileSync(file,'utf8'),script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
function run(width=736,{saved=null,failHost=false,reduced=false,noHost=false}={}){
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
  const context={document:{hidden:false,getElementById:()=>root,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),addEventListener:(k,f)=>dh[k]=f},window:{matchMedia:()=>({matches:reduced}),addEventListener:(k,f)=>wh[k]=f},performance:{now:()=>time},requestAnimationFrame:f=>{frames.set(++id,f);return id;},cancelAnimationFrame:i=>frames.delete(i)};
  if(!noHost)context.window.openai={widgetState:saved,setWidgetState:p=>{saves++;lastSaved=p;if(failHost)throw Error('Optional host unavailable');return Promise.resolve();}};
  vm.runInNewContext(script,context,{timeout:2000});
  const el=name=>root.querySelector(`[data-${name}]`),fire=(name,event,value)=>{const n=el(name);if(value!==undefined)n.value=value;n.handlers[event]({target:n});};
  const advance=ms=>{time+=ms;const todo=[...frames.values()];frames.clear();todo.forEach(f=>f(time));};
  const panels=root.querySelectorAll('section'),description=i=>panels[i].querySelector('svg').attrs['aria-label'];
  assert.strictEqual(panels.length,2);assert.strictEqual(saves,0,'No save on initialization');
  assert.strictEqual(el('time').textContent,saved&&!noHost?'48.0':'24.0');
  assert(panels.every(p=>p.querySelector('svg').children.length>20));
  fire('time-slider','input','24');assert.strictEqual(saves,0,'Scrub frames stay local');
  assert(description(0).includes('B record none'));assert(description(1).includes('memory 0.37'));
  fire('play','click');
  if(!reduced){advance(100);assert(Number(el('time').textContent)>24);fire('play','click');assert.strictEqual(frames.size,0);fire('play','click');for(let i=0;i<45;i++)advance(100);}
  assert.strictEqual(el('time').textContent,'32.0');assert.strictEqual(frames.size,0,'Pause at first rewrite');
  assert.strictEqual(el('play').textContent,'Continue feedback');
  assert(description(0).includes('B record flagged, next access 25 percent'));
  assert(description(1).includes('B record none, next access 100 percent'));
  assert(description(0).includes('memory 0.57'));assert(description(1).includes('memory 0.57'));
  fire('play','click');if(!reduced)for(let i=0;i<205;i++)advance(100);
  assert.strictEqual(el('time').textContent,'72.0');assert.strictEqual(frames.size,0,'Finite playback');
  assert.strictEqual(el('play').textContent,'Replay');
  assert(description(0).includes('observed route Familiar'));assert(description(1).includes('memory 0.86, observed route Explore'));
  fire('play','click');if(!reduced)for(let i=0;i<45;i++)advance(100);
  assert.strictEqual(el('time').textContent,'32.0','Replay returns to first intervention checkpoint');
  fire('time-slider','input','31.99');fire('time-slider','change');assert(description(0).includes('B record none'));
  fire('rewrite','click');assert(description(0).includes('B record flagged'));assert.strictEqual(frames.size,0);
  const beforeRestore=saves;
  wh['openai:set_globals']({detail:{globals:{widgetState:{privateContent:{id:'records-recreated',version:1,time:48}}}}});
  assert.strictEqual(el('time').textContent,'48.0');assert.strictEqual(saves,beforeRestore,'No save on restore');
  wh.resize();advance(100);assert.strictEqual(el('time').textContent,'48.0');
  if(!reduced){fire('play','click');context.document.hidden=true;dh.visibilitychange();assert.strictEqual(frames.size,0,'Hidden document pauses');}
  if(!noHost)assert(Buffer.byteLength(JSON.stringify(lastSaved))<16384);
  return {width,failHost,reduced,noHost,initialization:true,firstRewritePause:true,seekReplayRestore:true,finitePlayback:true};
}
const checks=[run(736),run(320),run(1024,{failHost:true}),run(360,{reduced:true}),run(736,{noHost:true}),run(736,{saved:{privateContent:{id:'records-recreated',version:1,time:48}}})];
const reportPath=__dirname+'/checks/records-recreated.json',report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
report.offlineControls=checks;report.visualInspection='Browser rendering not verified. Offline DOM/control checks are not browser layout checks.';
fs.writeFileSync(reportPath,JSON.stringify(report,null,2));console.log(JSON.stringify(checks,null,2));
