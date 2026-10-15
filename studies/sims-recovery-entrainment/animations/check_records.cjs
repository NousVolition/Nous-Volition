// Portable numerical, offline control and static export checks; no browser required.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),cp=require('child_process');
for(const name of ['check-records-model','check-records-controls','check-records-recreated-model','check-records-recreated-controls']){
  const result=cp.spawnSync(process.execPath,[path.join(__dirname,name+'.cjs')],{encoding:'utf8'});
  if(result.status!==0){process.stderr.write(result.stderr||result.stdout);process.exit(1);}
  console.log(name+': passed');
}
const decode=text=>text.replace(/&(quot|#x27|lt|gt|amp);/g,(_,s)=>({quot:'"','#x27':"'",lt:'<',gt:'>',amp:'&'}[s]));
const exportsChecked=[];
for(const name of ['records-and-memory','records-recreated']){
  const page=fs.readFileSync(path.join(__dirname,name+'.html'),'utf8').replace(/\r\n/g,'\n');
  const source=fs.readFileSync(path.join(__dirname,'source',name+'.html'),'utf8').replace(/\r\n/g,'\n');
  const match=page.match(/data-srcdoc="([^"]*)"/);assert(match,'Standalone wrapper contains an embedded document');
  const inner=decode(match[1]);assert(inner.includes(source),'Export preserves the complete source fragment');
  assert(!/<script\b[^>]*\bsrc=/i.test(inner),'No external script dependency');
  assert(!/[A-Za-z]:[\\/]+Users[\\/]/.test(page),'No private local paths');
  let scripts=0;for(const document of [page,inner])for(const s of document.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){if(/type="application\/json"/.test(s[1]))continue;new vm.Script(s[2]);scripts++;}
  exportsChecked.push({name,bytes:Buffer.byteLength(page),sourcePreserved:true,externalScripts:false,parsedScripts:scripts});
}
const report={status:'passed',exports:exportsChecked,browserRenderingVerified:false};
fs.writeFileSync(path.join(__dirname,'checks','record-exports.json'),JSON.stringify(report,null,2)+'\n');
console.log('Static exports: passed; browser rendering not verified.');
