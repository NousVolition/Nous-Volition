const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path').join(__dirname, '../fragments/sims-evidence-and-response.html');
const html = fs.readFileSync(path, 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(source, { filename: path });
const model = source.slice(source.indexOf('  const RULES='), source.indexOf('  function htmlEl'));
const context = vm.createContext({});
vm.runInContext(model + '\nglobalThis.model = { normalize, preset, build, bestFit };', context);
const m = context.model;
const results = ['mismatch', 'contrast'].map(name => {
  const config = m.normalize({ preset: name, mode: name === 'contrast' ? 'probe' : 'network', ...m.preset(name) });
  const run = m.build(config);
  const final = run.afterEvidence[run.afterEvidence.length - 1];
  return {
    setup: name,
    beforeActions: run.before.events.length,
    afterActions: run.after.events.length,
    participants: run.responses.map((r, i) => ({
      sim: i,
      evidence: run.packets[i].n,
      challenged: run.packets[i].challenged,
      policy: config.policies[i],
      claim: config.claims[i] + ' -> ' + run.afterConfig.claims[i],
      behavior: config.actual[i] + ' -> ' + run.afterConfig.actual[i],
      reply: r.message,
      freshActions: final[i].n,
      freshBest: m.bestFit(final[i]).best,
      freshSupport: m.bestFit(final[i]).maximum
    }))
  };
});
console.log(JSON.stringify(results, null, 2));
