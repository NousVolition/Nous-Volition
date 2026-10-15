const fs=require('fs'),vm=require('vm'),assert=require('assert');
const filename=require('path').join(__dirname,'source','records-and-memory.html');
const html=fs.readFileSync(filename,'utf8');
const source=html.slice(html.indexOf('const checkpoint=24'),html.indexOf('let time=0'));
const context={};vm.createContext(context);vm.runInContext(source+';this.model={checkpoint,duration,arms,tracks,snapshot,position,makeTrack,choose};',context);
const {arms,tracks,snapshot,position,makeTrack}=context.model;
const close=(a,b,msg)=>assert(Math.abs(a-b)<1e-11,msg||`${a} vs ${b}`);
const plain=x=>JSON.parse(JSON.stringify(x));
for(const arm of arms){
  assert.deepStrictEqual(plain(tracks[arm.id].slice(0,2)),plain(tracks.keep.slice(0,2)),'One shared pre-intervention history');
  const initial=snapshot(arm.id,0,false);assert.deepStrictEqual(plain(initial.memories),[.5,.5]);assert.strictEqual(initial.choices,null);
  for(let t=0;t<=72;t+=.03125)for(const m of snapshot(arm.id,t).memories)assert(m>=0&&m<=1,'Memory bounds');
}
const before=snapshot('keep',24,false),clearRecord=snapshot('record',24,true),clearMemory=snapshot('memory',24,true),both=snapshot('both',24,true);
assert.deepStrictEqual(plain(clearRecord.memories),plain(before.memories),'Record deletion preserves memory exactly');
assert.deepStrictEqual(plain(clearRecord.records),[0,0]);
assert.deepStrictEqual(plain(clearMemory.records),plain(before.records),'Memory reset preserves records');
assert.deepStrictEqual(plain(clearMemory.memories),[.5,.5]);
assert.deepStrictEqual(plain(both.records),[0,0]);assert.deepStrictEqual(plain(both.memories),[.5,.5]);
const nodes={start:{x:168,y:20},gate:{x:168,y:74},fork:{x:168,y:146},familiar:{x:62,y:194},explore:{x:274,y:194}};
for(const arm of arms)for(let owner=0;owner<2;owner++){
  assert.deepStrictEqual(plain(position(arm.id,24,owner,nodes)),plain(position('keep',24,owner,nodes)),'Resets preserve physical position');
  for(let v=0;v<6;v++)for(const offset of [0,1,2,5,7,9]){
    const t=12*v+offset;if(t<=0)continue;const a=position(arm.id,t-1e-8,owner,nodes),b=position(arm.id,t+1e-8,owner,nodes);
    assert(Math.hypot(a.x-b.x,a.y-b.y)<1e-5,'Movement is continuous at phase boundaries');
  }
}
for(const arm of arms){
  const swapped=makeTrack(arm,[1,0]);
  tracks[arm.id].forEach((v,i)=>{for(let owner=0;owner<2;owner++)close(v.end[owner],swapped[i].end[1-owner],'Identity cannot affect dynamics');});
  const equal=makeTrack(arm,[0,0]);equal.forEach(v=>close(v.end[0],v.end[1],'Equal records give equal trajectories'));
}
const outcomes={};let maxRK4Error=0;
for(const arm of arms){
  let m=[.5,.5],records=[0,1];
  for(let visit=0;visit<6;visit++){
    if(visit===2){if(arm.eraseRecord)records=[0,0];if(arm.eraseMemory)m=[.5,.5];}
    for(let step=0;step<300;step++)m=m.map((value,owner)=>{
      const target=1-.75*records[owner],f=x=>(target-x)/8,h=.01;
      const a=f(value),b=f(value+h*a/2),c=f(value+h*b/2),d=f(value+h*c);
      return value+h*(a+2*b+2*c+d)/6;
    });
    for(let owner=0;owner<2;owner++)maxRK4Error=Math.max(maxRK4Error,Math.abs(m[owner]-tracks[arm.id][visit].end[owner]));
  }
  outcomes[arm.id]={checkpoint:plain(snapshot(arm.id,24,true)),final:plain(snapshot(arm.id,72,true)),routes:tracks[arm.id].map(v=>v.choices)};
}
assert(maxRK4Error<1e-12);
const gap=s=>s.memories[0]-s.memories[1];
close(gap(snapshot('record',72)),gap(before)*Math.exp(-12/8),'After record deletion the memory gap decays');
close(gap(snapshot('memory',72)),.75*(1-Math.exp(-12/8)),'Retained records rebuild the memory gap');
close(gap(snapshot('both',72)),0,'Resetting both removes the differential cause');
assert.deepStrictEqual(plain(tracks.record[2].choices),['Explore','Familiar'],'First post-deletion route still reflects old memory');
assert.deepStrictEqual(plain(tracks.record[3].choices),['Explore','Explore'],'Later equal access changes B’s route');
assert.deepStrictEqual(plain(tracks.memory[2].choices),['Explore','Familiar'],'Record-driven difference returns after memory reset');
assert.deepStrictEqual(plain(tracks.both[2].choices),['Explore','Explore']);
assert(fs.statSync(filename).size<1e6);assert(!/\\"|\\n/.test(html));
const report={basis:'Assumed deterministic intervention model inspired by user-provided passages; no source-equation or empirical-validation claim.',protocol:{initialMemory:[.5,.5],initialRecords:[0,1],offeredAccess:[1,.25],memoryLearningTime:8,routeThreshold:.6,checkpoint:24,visits:6,visitDuration:3,interval:12,recordsFixed:true,simultaneousVisits:true},maxRK4Error,checks:['Identical initial memories and behaviour','Shared pre-intervention history','Field-specific resets','Position preservation','Continuous motion','Identity permutation','Equal-record counterfactual','Closed-form vs independent RK4','Memory-gap identities','Post-reset route outcomes'],outcomes};
fs.writeFileSync(__dirname+'/checks/records-memory.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({maxRK4Error,outcomes},null,2));
