const fs=require('fs'),vm=require('vm'),assert=require('assert');
const base=require('path').join(__dirname,'source')+'/';
const html=fs.readFileSync(base+'records-recreated.html','utf8');
const source=html.slice(html.indexOf('const checkpoint=24'),html.indexOf('let time=checkpoint'));
const context={};vm.createContext(context);vm.runInContext(source+';this.model={checkpoint,firstRewrite,duration,arms,tracks,snapshot,makeTrack,choose,classify};',context);
const {tracks,snapshot,makeTrack}=context.model;
const plain=x=>JSON.parse(JSON.stringify(x)),close=(a,b,msg)=>assert(Math.abs(a-b)<1e-11,msg||`${a} vs ${b}`);
const previous=fs.readFileSync(base+'records-and-memory.html','utf8'),old={};vm.createContext(old);
vm.runInContext(previous.slice(previous.indexOf('const checkpoint=24'),previous.indexOf('let time=0'))+';this.model={tracks,snapshot};',old);
for(const id of ['rewrite','off']){
  const initial=snapshot(id,0);assert.deepStrictEqual(plain(initial.memories),[.5,.5]);
  assert.deepStrictEqual(plain(snapshot(id,24).records),[0,0]);
  assert.deepStrictEqual(plain(snapshot(id,24).memories),plain(old.model.snapshot('keep',24,false).memories),'Erasure preserves memory exactly');
  assert.deepStrictEqual(plain(tracks[id].slice(0,2)),plain(tracks.off.slice(0,2)),'Shared earlier history');
  for(let t=0;t<=72;t+=.03125)for(const m of snapshot(id,t).memories)assert(m>=0&&m<=1);
  for(const v of tracks[id])assert(v.leave<v.observation&&v.observation<v.review&&v.review<v.depart+12,'Learning precedes new behaviour, which precedes review and next visit');
}
for(let t=24;t<=72;t+=.03125){
  const before=old.model.snapshot('record',t),now=snapshot('off',t);
  assert.deepStrictEqual(plain(before.memories),plain(now.memories),'Disabled reclassification reproduces previous record-erasure arm exactly');
  assert.deepStrictEqual(plain(before.records),plain(now.records));
  close(snapshot('rewrite',t).memories[0],now.memories[0],'A unaffected by write switch');
}
for(let t=24;t<=38;t+=.03125)assert.deepStrictEqual(plain(snapshot('rewrite',t).memories),plain(snapshot('off',t).memories),'Memory changes only when later treatment changes');
assert.deepStrictEqual(plain(snapshot('rewrite',31.999).records),[0,0]);
assert.deepStrictEqual(plain(snapshot('rewrite',32).records),[0,1]);
assert.deepStrictEqual(plain(snapshot('off',32).records),[0,0]);
assert.deepStrictEqual(plain(snapshot('rewrite',32).visitAccess),[1,1],'No retroactive treatment');
assert.deepStrictEqual(plain(snapshot('rewrite',32).nextAccess),[1,.25]);
assert.deepStrictEqual(plain(snapshot('rewrite',31).choices),['Explore','Familiar']);
assert.deepStrictEqual(plain(snapshot('off',31).choices),['Explore','Familiar']);
assert.deepStrictEqual(plain(snapshot('off',43).choices),['Explore','Explore']);
assert.deepStrictEqual(plain(snapshot('rewrite',43).choices),['Explore','Familiar']);
assert(snapshot('rewrite',38.01).memories[1]<snapshot('off',38.01).memories[1]);
let maxRK4Error=0;
for(const enabled of [true,false]){
  const id=enabled?'rewrite':'off',swapped=makeTrack(enabled,[1,0]),equal=makeTrack(enabled,[0,0]);
  let m=[.5,.5],records=[0,1];
  for(let visit=0;visit<6;visit++){
    if(visit===2)records=[0,0];
    for(let step=0;step<300;step++)m=m.map((value,owner)=>{
      const target=1-.75*records[owner],f=x=>(target-x)/8,h=.01;
      const a=f(value),b=f(value+h*a/2),c=f(value+h*b/2),d=f(value+h*c);
      return value+h*(a+2*b+2*c+d)/6;
    });
    if(visit>=2&&enabled)records=m.map(x=>x>=.6?0:1);
    for(let owner=0;owner<2;owner++){
      const v=tracks[id][visit];
      maxRK4Error=Math.max(maxRK4Error,Math.abs(m[owner]-v.end[owner]));
      assert.strictEqual(records[owner],v.recordsAfter[owner]);
      close(v.end[owner],swapped[visit].end[1-owner],'Identity permutation symmetry');
      assert.strictEqual(v.recordsAfter[owner],swapped[visit].recordsAfter[1-owner]);
    }
    close(equal[visit].end[0],equal[visit].end[1],'Equal histories remain equal');
  }
}
assert(maxRK4Error<1e-12);
assert(fs.statSync(base+'records-recreated.html').size<1e6);assert(!/\\"|\\n/.test(html));
const report={basis:'Illustrative causal experiment; classifier and access rules assumed, not empirically calibrated.',protocol:{initialMemory:[.5,.5],initialRecords:[0,1],eraseTime:24,firstNewObservation:31,firstRewrite:32,firstAffectedArrival:38,learningTime:8,threshold:.6,rule:'new Familiar route -> flag; new Explore route -> no flag',simultaneousVisits:true,scheduledVisits:true},maxRK4Error,checks:['Shared pre-erasure history','Exact memory preservation','Disabled arm matches previous model','No reclassification before a new observation','No retroactive treatment','Memory difference only after treatment difference','Identity permutation symmetry','Equal-history counterfactual','Closed form versus independent RK4'],outcomes:Object.fromEntries(['rewrite','off'].map(id=>[id,{checkpoint:plain(snapshot(id,24)),firstRewrite:plain(snapshot(id,32)),final:plain(snapshot(id,72)),routes:tracks[id].map(v=>v.choices)}]))};
fs.writeFileSync(__dirname+'/checks/records-recreated.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({maxRK4Error,final:Object.fromEntries(Object.entries(report.outcomes).map(([id,x])=>[id,x.final]))},null,2));
