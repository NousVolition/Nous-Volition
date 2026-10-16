const fs=require('node:fs'),vm=require('node:vm');
const path=require('node:path').join(__dirname, '../fragments/sims-repeated-rounds.html');
const html=fs.readFileSync(path,'utf8'),source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(source,{filename:path});
const core=source.slice(source.indexOf('  const RULES='),source.indexOf('  function htmlEl'));
const context=vm.createContext({});
vm.runInContext(core+'\nglobalThis.model={normalize,preset,build,bestFit};',context);
const m=context.model;
const output=['current','contrast'].map(name=>{
  const c=m.normalize({preset:name,...m.preset(name),mode:name==='contrast'?'probe':'network'});
  const series=m.build(c);
  return {
    setup:name,rounds:c.roundCount,
    beforeActions:series.rounds[0].before.events.length,
    history:Array.from({length:9},(_,i)=>({sim:i,codes:series.rounds.map(r=>r.outcomes[i].code),claim:c.claims[i]+' -> '+series.rounds.at(-1).afterConfig.claims[i],behavior:c.actual[i]+' -> '+series.rounds.at(-1).afterConfig.actual[i],promises:series.rounds.map(r=>r.promiseChecks[i]?.status??null)})),
    roundTwoPromiseDialogue:series.rounds[1].packets[6].previousPromise,
    actionBlocks:series.rounds.map(r=>r.after.events.length)
  };
});
console.log(JSON.stringify(output,null,2));
