// Logic/finite-coordinate checks with a DOM/canvas stand-in, not a layout test.
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');const root=__dirname;
const html=fs.readFileSync(path.join(root,'player.html'),'utf8');let coordinates=0;
const finite=(...args)=>{args.forEach(x=>assert(Number.isFinite(x),'non-finite canvas coordinate'));coordinates++};
const ctx=new Proxy({measureText:s=>({width:s.length*8}),moveTo:finite,lineTo:finite,arc:finite,ellipse:finite,clearRect:finite,fillText:(s,x,y)=>finite(x,y),setLineDash:()=>{}},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>{o[k]=v;return true}});
const elements={};for(const id of ['setting','clip','speed','play','seek','readout','verdict','plot'])elements[id]={value:id==='speed'?'.5':'0',textContent:'',innerHTML:'',getContext:()=>ctx,width:1080,height:455};
const box={document:{getElementById:id=>elements[id]},atob:s=>Buffer.from(s,'base64').toString('binary'),Uint8Array,Float32Array,Math,Number,requestAnimationFrame:()=>{},console};vm.createContext(box);
vm.runInContext(fs.readFileSync(path.join(root,'animation-data.js'),'utf8'),box);const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];assert(scripts.length===1);vm.runInContext(scripts[0][1],box);
let states=0;for(let s=0;s<8;s++)for(let c=0;c<4;c++)for(const f of [0,75,150]){elements.setting.value=String(s);elements.clip.value=String(c);elements.seek.value=String(f);const got=vm.runInContext('render()',box);assert(got.dataset===s&&got.clip===c&&got.frame===f);assert(elements.readout.textContent.includes('simulation'));states++}
elements.play.onclick();assert(elements.play.textContent==='Play');elements.play.onclick();assert(elements.play.textContent==='Pause');elements.clip.oninput();assert(elements.seek.value==='0');
vm.runInContext(`for(const s of sets){if(s.q.length!==D.frames*6||s.delta.length!==D.frames*3*32)throw Error('shape');for(const k of ['q','delta','amplitude','repeat'])for(const v of s[k])if(!Number.isFinite(v))throw Error('nonfinite')}if(D.displayGain!==1)throw Error('display gain');`,box);
console.log(JSON.stringify({passed:true,states,coordinateCalls:coordinates,scope:'Offline controls and data, not browser layout'}));
