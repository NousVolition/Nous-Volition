/* Local-only entry. Pure conversion functions are exported for verification. */
(function(root){
  'use strict';
  const headers=['time_s','force_N','displacement_mm','velocity_mm_s','active_force_N','orbit_force_N'];
  function number(value,label){
    if(value===null||value===undefined||String(value).trim()==='')return null;
    if(typeof value==='boolean'||!/^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/.test(String(value).trim()))throw Error(label+': enter a number');
    const n=Number(value);if(!Number.isFinite(n))throw Error(label+': enter a finite number');return n;
  }
  function parseRows(text){
    const lines=text.replace(/^\uFEFF/,'').split(/\r?\n/).filter(x=>x.trim());if(!lines.length)return [];
    const delimiter=lines[0].includes('\t')?'\t':',';
    const names=lines.shift().split(delimiter).map(x=>x.trim());
    if(names.length!==headers.length||names.some((x,i)=>x!==headers[i]))throw Error('Use the six column names in the downloadable template, in that order.');
    return lines.map((line,i)=>{const cells=line.split(delimiter);if(cells.length!==headers.length)throw Error('Row '+(i+2)+': expected six columns');return Object.fromEntries(headers.map((h,j)=>[h,number(cells[j],'Row '+(i+2)+' '+h)]));});
  }
  function toCSV(rows){return headers.join(',')+'\n'+rows.map(r=>headers.map(h=>r[h]??'').join(',')).join('\n')+(rows.length?'\n':'');}
  function checkTrial(t){
    const issues=[];if(!t.samples.length)return ['Awaiting measurements'];
    if(t.samples.length<12)issues.push('At least 12 samples required');
    let required=['time_s','displacement_mm'];
    if(t.kind!=='feedback')required.push('force_N');
    if(t.kind==='feedback')required.push('velocity_mm_s','active_force_N');
    if(['circular','eccentric'].includes(t.kind))required.push('orbit_force_N');
    t.samples.forEach((r,i)=>{required.forEach(h=>{if(r[h]===null||!Number.isFinite(r[h]))issues.push('Row '+(i+1)+': missing '+h);});
      headers.forEach(h=>{if(r[h]!=null&&!Number.isFinite(r[h]))issues.push('Row '+(i+1)+': invalid '+h);});
      if(r.time_s<0||(i&&r.time_s<=t.samples[i-1].time_s))issues.push('Times must be nonnegative and strictly increasing');
      if(t.kind==='passive'&&((r.active_force_N||0)!==0||(r.orbit_force_N||0)!==0))issues.push('Turn actuator and orbital force off for passive trials');
      if(t.kind==='autonomous'&&(Math.abs(r.force_N||0)>1e-15||Math.abs(r.orbit_force_N||0)>1e-15))issues.push('Split off the push: autonomous recordings require zero external/orbital force');
    });
    if(t.kind!=='feedback'&&(!t.initial.known||['delayed_strain','viscous_strain','velocity_mm_s'].some(k=>!Number.isFinite(t.initial[k]))))issues.push('Document initial memory and velocity');
    if(['feedback','autonomous','circular','eccentric'].includes(t.kind)&&(!Number.isFinite(t.controller_delay_s)||t.controller_delay_s<0||t.controller_delay_s>t.samples.at(-1).time_s-t.samples[0].time_s))issues.push('Enter a measured controller delay within the recording duration');
    if(['autonomous','circular','eccentric'].includes(t.kind)&&t.controller_delay_s>0&&!t.initial.constant_delay_history_known)issues.push('Document constant initial controller history for delayed prediction');
    if(t.role==='fit'&&['autonomous','circular','eccentric'].includes(t.kind))issues.push('Reserve active motion and orbit recordings for validation');
    return [...new Set(issues)];
  }
  const api={headers,number,parseRows,toCSV,checkTrial};
  if(typeof module!=='undefined')module.exports=api;
  root.HugEntry=api;
  if(typeof document==='undefined')return;
  const $=id=>document.getElementById(id);let session,index=0;
  const metadata=['title','specimen_id','environment.water_mass_fraction','environment.temperature_C','instrument.force_resolution_N','instrument.displacement_resolution_mm','instrument.sampling_note','geometry.coupon_area_mm2','geometry.coupon_gap_mm','geometry.mode_length_mm','geometry.mode_volume_mm3','initial_guess.material.G_M_Pa','initial_guess.material.eta_M_Pa_s','initial_guess.material.G_K_Pa','initial_guess.material.eta_K_Pa_s','initial_guess.effective_mass_kg','initial_guess.parallel_stiffness_N_m','acceptance.displacement_rmse_mm','acceptance.force_rmse_N'];
  function get(path){return path.split('.').reduce((v,k)=>v[k],session);}
  function set(path,v){const ks=path.split('.'),last=ks.pop();ks.reduce((o,k)=>o[k],session)[last]=v;}
  function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function notice(text,error=false){$('notice').textContent=text;$('notice').className=error?'error':'notice';}
  function save(){
    metadata.forEach(p=>set(p,$(p).type==='number'?number($(p).value,p):$(p).value));
    session.data_origin=$('origin').value;
    const t=session.trials[index];t.id=$('trial-id').value.trim();t.kind=$('kind').value;t.role=$('role').value;t.notes=$('notes').value;
    t.controller_delay_s=number($('delay').value,'Controller delay');t.initial={known:$('known').checked,constant_delay_history_known:$('history').checked,
      delayed_strain:number($('u').value,'Initial delayed strain'),viscous_strain:number($('w').value,'Initial viscous strain'),velocity_mm_s:number($('v').value,'Initial velocity')};
    t.samples=parseRows($('rows').value);
    if(!t.id||session.trials.some((o,j)=>j!==index&&o.id===t.id))throw Error('Enter a unique, nonempty trial name');
  }
  function render(){
    metadata.forEach(p=>{$(p).value=get(p)??'';});$('origin').value=session.data_origin;
    $('trials').replaceChildren(...session.trials.map((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.id+' · '+t.kind+' · '+t.role+' · '+t.samples.length+' rows';return o;}));$('trials').value=index;
    const t=session.trials[index];$('trial-id').value=t.id;$('kind').value=t.kind;$('role').value=t.role;$('notes').value=t.notes||'';$('delay').value=t.controller_delay_s??'';$('known').checked=t.initial.known===true;$('history').checked=t.initial.constant_delay_history_known===true;
    ['u','w','v'].forEach((id,i)=>{$(id).value=t.initial[['delayed_strain','viscous_strain','velocity_mm_s'][i]]??'';});$('rows').value=toCSV(t.samples);
  }
  function guarded(action){return async()=>{try{await action();}catch(e){notice(e.message,true);}};}
  $('check').onclick=guarded(()=>{save();const issues=checkTrial(session.trials[index]);notice(issues.length?issues.join(' · '):'This recording is ready for analysis. Fit quality and validation still need to be tested.',issues.length>0);render();});
  $('trials').onchange=guarded(()=>{const next=Number($('trials').value);save();index=next;render();notice('Recording selected.');});
  $('add').onclick=guarded(()=>{save();let n=session.trials.length+1;while(session.trials.some(t=>t.id==='trial-'+n))n++;
    session.trials.push({id:'trial-'+n,kind:'creep',role:'validation',notes:'',controller_delay_s:null,initial:{known:false,delayed_strain:null,viscous_strain:null,velocity_mm_s:null,constant_delay_history_known:false},samples:[]});index=session.trials.length-1;render();notice('Added an empty recording.');});
  $('export').onclick=guarded(()=>{save();download('hug-measurements.json',JSON.stringify(session,null,2)+'\n','application/json');notice('Downloaded your measurements. They were not uploaded. Keep this file outside the published study folder.');render();});
  $('csv').onclick=()=>download('measurement_template.csv',toCSV([]),'text/csv');
  $('import').onchange=guarded(async()=>{const f=$('import').files[0];if(!f)return;const candidate=JSON.parse(await f.text());
    if(candidate.schema_version!==1||!['physical','synthetic'].includes(candidate.data_origin)||!Array.isArray(candidate.trials)||!candidate.trials.length)throw Error('Unsupported session. Use the supplied template.');
    if(metadata.some(p=>{try{return p.split('.').reduce((v,k)=>v[k],candidate)===undefined;}catch(e){return true;}}))throw Error('Session is missing required metadata fields');
    const seen=new Set();for(const t of candidate.trials){if(!t.id||seen.has(t.id)||!['creep','passive','feedback','autonomous','circular','eccentric'].includes(t.kind)||!['fit','validation'].includes(t.role)||!t.initial||!Array.isArray(t.samples))throw Error('Invalid trial metadata');seen.add(t.id);t.samples=parseRows(toCSV(t.samples));}
    session=candidate;index=0;render();notice('Imported locally. No upload occurred.');});
  $('csv-import').onchange=guarded(async()=>{const f=$('csv-import').files[0];if(!f)return;const rows=parseRows(await f.text());$('rows').value=toCSV(rows);notice('Loaded '+rows.length+' rows into the current recording.');});
  // Embedded blank template keeps file:// entry usable without fetching local files.
  session=JSON.parse($('blank').textContent);render();notice('Awaiting measurements. Starting guesses are not measured results.');
})(typeof globalThis!=='undefined'?globalThis:this);
