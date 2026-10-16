// Recompute the saved simulation, without a browser or third-party packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'snapshots/latest-run.json'), 'utf8'));
const html = fs.readFileSync(path.join(root, 'fragments/sims-repeated-rounds.html'), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const core = source.slice(source.indexOf('  const RULES='), source.indexOf('  function htmlEl'));
const context = vm.createContext({});
vm.runInContext(core + '\nglobalThis.model={normalize,build,bestFit};', context);
const m = context.model;
const config = m.normalize(snapshot.modelContent.config);
const series = m.build(config);
const result = {
  model: snapshot.modelContent.model,
  config,
  baselineActions: series.rounds[0].before.events.length,
  rounds: series.rounds.map(r => ({
    round: r.index + 1,
    observedActions: r.after.events.length,
    participants: r.responses.map((response, i) => ({
      sim: i,
      challenged: r.packets[i].challenged,
      claimBefore: r.beforeConfig.claims[i],
      claimAfter: r.afterConfig.claims[i],
      behaviorBefore: r.beforeConfig.actual[i],
      behaviorAfter: r.afterConfig.actual[i],
      responsePolicy: response.policy,
      response: response.message,
      change: r.outcomes[i].code,
      promised: response.promised,
      promiseAssessment: r.promiseChecks[i],
      freshActions: r.afterEvidence.at(-1)[i].n,
      freshSupport: m.bestFit(r.afterEvidence.at(-1)[i]).w
    }))
  }))
};
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
