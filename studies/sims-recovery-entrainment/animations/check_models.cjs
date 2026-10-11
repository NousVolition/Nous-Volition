const fs=require('fs'),assert=require('assert'),path=require('path');

(()=>{
const source=fs.readFileSync(path.join(__dirname,'source','within-and-position.html'),'utf8');
const math=source.slice(source.indexOf('const duration=14'),source.indexOf('let time=0'));
const model=new Function(math+'return {trajectory,tracks,step,duration,drive};')();
let maxRefinement=0;
for(const kind of ['move','internal']){
  const fine=model.trajectory(kind,model.step/2),original=model.tracks[kind];
  for(let i=0;i<original.length;i++)maxRefinement=Math.max(maxRefinement,Math.abs(original[i]-fine[2*i]));
  const after=original[Math.round(9/model.step)],target=kind==='move'?-1:1;
  assert(Math.abs(original.at(-1)-(target+(after-target)*Math.exp(-5)))<1e-10);
}
assert(maxRefinement<1e-8);
for(let i=0;i<=Math.round(7/model.step);i++)assert.strictEqual(model.tracks.move[i],model.tracks.internal[i]);
assert(model.tracks.move.at(-1)<-.99 && model.tracks.internal.at(-1)>.99);
console.log('within-and-position: numerical checks passed');
})();

(()=>{
const source=fs.readFileSync(path.join(__dirname,'source','moving-with-memory.html'),'utf8');
const math=source.slice(source.indexOf('const duration=32'),source.indexOf('let time=0'));
const model=new Function(math+'return {trajectory,tracks,step,duration,causes};')();
let maxRefinement=0,maxLateError=0;
const final=[];
for(const tau of [0,12])for(const kind of ['memory','control']){
  const a=model.trajectory(kind,model.step,tau),fine=model.trajectory(kind,model.step/2,tau);
  const at9=a[Math.round(9/model.step)],rate=tau>0?1/tau:0;
  for(let i=0;i<a.length;i++){
    for(const key of ['m','x']){
      assert(Number.isFinite(a[i][key]));maxRefinement=Math.max(maxRefinement,Math.abs(a[i][key]-fine[2*i][key]));
    }
    assert(a[i].m>=-1e-10&&a[i].m<=2+1e-10&&a[i].x>=-1-1e-10&&a[i].x<=3+1e-10);
    if(kind==='control')assert.strictEqual(a[i].m,0);
    if(i<=Math.round(2/model.step))assert.deepStrictEqual(a[i],{x:-1,m:0});
    if(i>=Math.round(9/model.step)){
      const s=i*model.step-9;
      const expectedM=at9.m*Math.exp(-rate*s);
      const expectedX=-1+(at9.x+1)*Math.exp(-s)+at9.m*(Math.exp(-rate*s)-Math.exp(-s))/(1-rate);
      maxLateError=Math.max(maxLateError,Math.abs(a[i].m-expectedM),Math.abs(a[i].x-expectedX));
    }
  }
  if(kind==='memory'&&tau===0)assert(Math.abs(at9.m-2*(1-Math.exp(-3)))<1e-10);
  if(kind==='memory'&&tau===12)assert(a.at(-1).m<at9.m);
  final.push({kind,tau,...a.at(-1)});
}
assert(maxRefinement<1e-8);assert(maxLateError<1e-9);
console.log('moving-with-memory: numerical checks passed');
})();

(()=>{
const source=fs.readFileSync(path.join(__dirname,'source','memory-next-path.html'),'utf8');
const model=new Function(source.slice(source.indexOf('const duration=32'),source.indexOf('let time=0'))+'return {trajectory,sample,decision,step};')();
const outcomes=[];let maxRefinement=0,maxAnalyticError=0;
for(const tau of [0,12])for(const kind of ['memory','control']){
 const points=model.trajectory(kind,model.step,tau),fine=model.trajectory(kind,model.step/2,tau);
 for(let i=0;i<points.length;i++){
  assert(Number.isFinite(points[i])&&points[i]>=-1e-10&&points[i]<=2+1e-10);
  if(kind==='control'||i<=2/model.step)assert.strictEqual(points[i],0);
  maxRefinement=Math.max(maxRefinement,Math.abs(points[i]-fine[2*i]));
  if(i>=9/model.step)maxAnalyticError=Math.max(maxAnalyticError,Math.abs(points[i]-points[9/model.step]*Math.exp(tau?-(i*model.step-9)/tau:0)));
 }
 if(tau===0&&kind==='memory')assert(Math.abs(points[9/model.step]-2*(1-Math.exp(-3)))<1e-10);
 for(const arrive of [14,26]){
  const choice=model.decision(points,arrive),expected=kind==='control'||(tau===12&&arrive===26)?'familiar':'explore';
  assert.strictEqual(choice,expected);outcomes.push({kind,tau,arrive,memory:model.sample(points,arrive),choice});
 }
}
assert(maxRefinement<1e-8&&maxAnalyticError<1e-9);
console.log('memory-next-path: numerical checks passed');
})();

(()=>{
const source=fs.readFileSync(path.join(__dirname,'source','memory-journey-cycle.html'),'utf8');
const model=new Function(source.slice(source.indexOf('const duration=44'),source.indexOf('let time=0'))+'return {trajectory,choose,target,step};')();
const outcomes=[];let maxRefinement=0,maxAnalyticError=0;
for(const tau of [0,12])for(const mode of ['balancing','reinforcing'])for(const kind of ['memory','control']){
 const run=model.trajectory(kind,model.step,tau,mode),fine=model.trajectory(kind,model.step/2,tau,mode),points=run.points;
 assert.deepStrictEqual(run.trips.map(t=>t.destination),fine.trips.map(t=>t.destination));
 for(let i=0;i<points.length;i++){
  assert(Number.isFinite(points[i])&&points[i]>=-1e-10&&points[i]<=2+1e-10);
  if(kind==='control'||i<=2/model.step)assert.strictEqual(points[i],0);
  maxRefinement=Math.max(maxRefinement,Math.abs(points[i]-fine.points[2*i]));
 }
 if(tau===0&&kind==='memory')assert(Math.abs(points[9/model.step]-2*(1-Math.exp(-3)))<1e-10);
 for(const trip of run.trips){
  assert.strictEqual(trip.destination,model.choose(points[Math.round(trip.fork/model.step)]));
  const initial=points[Math.round(trip.arrival/model.step)],aim=model.target(trip.destination,mode);
  for(let i=Math.round(trip.arrival/model.step);i<=Math.round(trip.leave/model.step);i++){
   const expected=kind==='control'?0:aim+(initial-aim)*Math.exp(-.6*(i*model.step-trip.arrival));
   maxAnalyticError=Math.max(maxAnalyticError,Math.abs(points[i]-expected));
  }
 }
 const expected=kind==='control'?['familiar','familiar','familiar']:mode==='balancing'?['explore','familiar','explore']:['explore','explore','explore'];
 assert.deepStrictEqual(run.trips.map(t=>t.destination),expected);
 outcomes.push({kind,tau,mode,trips:run.trips,finalMemory:points.at(-1)});
}
assert(maxRefinement<1e-8&&maxAnalyticError<1e-9);
// Sensitivity control: disabling the memory-to-choice link yields only Familiar,
// even though the same destination update law remains enabled.
const fixedSource=source.slice(source.indexOf('const duration=44'),source.indexOf('let time=0')).replace("const choose=m=>m>threshold?'explore':'familiar';","const choose=m=>'familiar';");
const fixedModel=new Function(fixedSource+'return {trajectory};')();
assert.deepStrictEqual(fixedModel.trajectory('memory',.005,0,'balancing').trips.map(t=>t.destination),['familiar','familiar','familiar']);
console.log('memory-journey-cycle: numerical checks passed');
})();
