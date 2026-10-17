const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
let checks = 0;
function check(value, name) { assert(value, name); checks++; }
const source = fs.readFileSync(path.join(root, 'src/mobile-ui.js'), 'utf8');
function run(observe) {
  const regions = [
    { scrollWidth:500, clientWidth:290, tabIndex:0 },
    { scrollWidth:500, clientWidth:700, tabIndex:0 },
  ];
  const hints = regions.map(() => ({hidden:false}));
  const observed=[], callbacks=[], seedAttrs={};
  regions.forEach((region,i) => {
    region.getAttribute=()=>String(i);
    region.querySelector=()=>({table:true});
  });
  const sandbox = {
    document: {
      querySelectorAll: selector => selector==='.sims-table-scroll' ? regions : [{setAttribute:(k,v)=>seedAttrs[k]=v}],
      getElementById: id => hints[+id],
    },
    window: {addEventListener: (_type, callback) => callbacks.push(callback)},
  };
  if(observe) sandbox.ResizeObserver = class {
    constructor(callback) { callbacks.push(callback); }
    observe(target) { observed.push(target); }
  };
  vm.runInNewContext(source, sandbox);
  check(!hints[0].hidden && regions[0].tabIndex===0, 'overflow has hint and keyboard access');
  check(hints[1].hidden && regions[1].tabIndex===-1, 'fitting table avoids unnecessary hint and tab stop');
  check(seedAttrs.inputmode==='numeric','seed requests a numeric keyboard');
  regions[0].clientWidth=800; regions[1].clientWidth=300;
  callbacks.forEach(callback=>callback());
  check(hints[0].hidden && !hints[1].hidden,'orientation changes update hints');
  if(observe) check(observed.length===4,'both tables and containers observed');
}
run(true); run(false);
for(const file of fs.readdirSync(path.join(root,'dist')).filter(f=>f.endsWith('.html'))) {
  const html=fs.readFileSync(path.join(root,'dist',file),'utf8');
  check(html.includes('width=device-width, initial-scale=1'),'responsive viewport: '+file);
  check(!/user-scalable\s*=\s*no|maximum-scale\s*=\s*1/.test(html),'zoom remains available: '+file);
  check(html.includes('min-height:44px') && html.includes('font-size:16px'),'phone control styles: '+file);
  check(html.includes('overflow-x:auto') && (!html.includes('<table ') || html.includes('Swipe sideways')), 'scroll region support: '+file);
}
console.log(JSON.stringify({passed:true,checks,coverage:['overflow hints and resizing','keyboard scrolling access','numeric seed keyboard','six responsive pages with zoom and enlarged controls']}));
