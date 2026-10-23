"""Reproduce the declared within-person measurement probes; not a corpus PDE fit."""
from pathlib import Path
import argparse, csv, hashlib, json, collections
import numpy as np

ROOT = Path(__file__).resolve().parent
RATINGS = {'Agree': 1, 'Partiallyagree': 1, 'Neitheragree nordisagree': 0,
           'Partiallydisagree': 0, 'Disagree': 0}
SEED = 20261022

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def eligible(r):
    return r['exp_type'].replace(' ', '') == 'Innervoice' and r['dial'].replace(' ', '') in {k.replace(' ', '') for k in RATINGS}

def prepare_inner(raw, cohort):
    groups = collections.defaultdict(list)
    for r in raw: groups[r['participant']].append(r)
    rows = []
    missing = collections.Counter()
    for i, key in enumerate(sorted(groups), 1):
        g = sorted(groups[key], key=lambda r: float(r['time_elapsed']))
        times = [float(r['time_elapsed']) for r in g]
        assert all(b > a for a, b in zip(times, times[1:])), 'Non-strict chronology'
        for j, r in enumerate(g):
            r = dict(r, exp_type=r['exp_type'].replace(' ', ''), dial=r['dial'].replace(' ', ''))
            good = eligible(r)
            missing['inner_voice_reports' if r['exp_type'] == 'Innervoice' else 'other_experience_reports'] += 1
            if r['exp_type'] == 'Innervoice' and not good: missing['inner_voice_missing_dialogic'] += 1
            rows.append(dict(person=f'{cohort}{i:04d}', probe=j+1,
                elapsed_seconds=(times[j]-times[0])/1000,
                eligible=int(good), dialogic={k.replace(' ', ''):v for k,v in RATINGS.items()}[r['dial']] if good else '',
                strict_dialogic=int(r['dial']=='Agree') if good else ''))
    return rows, dict(rows=len(raw), people=len(groups), **missing)

def groups_of(rows):
    g = collections.defaultdict(list)
    for r in rows: g[r['person']].append(r)
    for k in g: g[k].sort(key=lambda r: int(r['probe']))
    return g

def population(rows, outcome):
    means = []
    for g in groups_of(rows).values():
        y = [int(r[outcome]) for r in g if int(r['eligible'])]
        if y: means.append(np.mean(y))
    return float(np.mean(means))

def predict(rows, prior, strength, outcome='dialogic'):
    out = []
    for person, g in groups_of(rows).items():
        past = []
        for r in g:
            if not int(r['eligible']): continue
            y = int(r[outcome])
            if past:
                p = (sum(past)+strength*prior)/(len(past)+strength)
                out.append(dict(person=person, probe=int(r['probe']), past_n=len(past),
                    y=y, population=prior, last=past[-1], history=p))
            past.append(y)
    return out

def person_scores(pred):
    out=[]
    for person, g in groups_of(pred).items():
        out.append(dict(person=person, n=len(g), **{m: float(np.mean([(r[m]-r['y'])**2 for r in g])) for m in ['population','last','history']}))
    return out

def interval(values):
    if not len(values): raise ValueError('No eligible values; inspect inclusion audit')
    x=np.array(values, dtype=float); rng=np.random.default_rng(SEED)
    means=np.array([np.mean(rng.choice(x, size=len(x), replace=True)) for _ in range(2000)])
    return dict(mean=float(x.mean()), ci95=np.quantile(means,[.025,.975]).tolist(), people=len(x))

def inner_analysis(train, test, outcome):
    prior=population(train,outcome)
    tuning=[]
    for strength in [1,2,4,8,16]:
        scores=person_scores(predict(train,prior,strength,outcome))
        tuning.append(dict(strength=strength, brier=float(np.mean([r['history'] for r in scores]))))
    chosen=min(tuning,key=lambda r:(r['brier'],r['strength']))['strength']
    preds=predict(test,prior,chosen,outcome); scores=person_scores(preds)
    result=dict(outcome=outcome, population_probability=prior, chosen_strength=chosen,
        tuning=tuning, evaluation_people=len(scores), evaluation_predictions=len(preds),
        brier={m:float(np.mean([r[m] for r in scores])) for m in ['population','last','history']},
        history_minus_population=interval([r['history']-r['population'] for r in scores]),
        history_minus_last=interval([r['history']-r['last'] for r in scores]))
    return result,preds,scores

def prepare_cram(raw):
    fields=['Places','Times','People','Things','Feelings','Context','Details','Episodes']
    key='Temporal Bin (Youth) Assigned to Memory (0-9)'
    people={p:i for i,p in enumerate(sorted({r['Test/Subject ID'] for r in raw}),1)}
    reasons=collections.Counter(); out=[]
    for r in raw:
        try:
            values=[float(r[f]) for f in fields]; total=float(r['Total content'])
            if not all(np.isfinite(v) and v>=0 and v.is_integer() for v in values+[total]):
                reasons['invalid_content']+=1;continue
        except (ValueError,TypeError): reasons['missing_content']+=1;continue
        if sum(values)!=total: reasons['sum_mismatch']+=1;continue
        try:
            youth=float(r[key]); bins=float(r['Number of Temporal Bins (Youths) Selected']); age=float(r['Age'])
            if bins!=1 or not youth.is_integer() or youth not in range(10):
                reasons['non_single_or_invalid_bin']+=1;continue
            if not np.isfinite(age) or not 0<age<=120: reasons['invalid_age']+=1;continue
        except (ValueError,TypeError): reasons['invalid_age_or_bin']+=1;continue
        out.append(dict(person=f'C{people[r["Test/Subject ID"]]:05d}',
            probe=len(out)+1, youth_bin=int(youth), total_content=int(total)))
    return out,dict(raw_rows=len(raw),raw_people=len(people),included_rows=len(out),
        included_people=len({r['person'] for r in out}),exclusions=dict(reasons))

def cram_analysis(rows):
    summaries=[]
    for person,g in groups_of(rows).items():
        old=np.array([float(r['total_content']) for r in g if int(r['youth_bin'])<=7])
        new=np.array([float(r['total_content']) for r in g if int(r['youth_bin'])>=8])
        if len(old) and len(new):
            dif=old[:,None]-new[None,:]
            summaries.append(dict(person=person,n_remote=len(old),n_recent=len(new),
                remote_mean=float(old.mean()),recent_mean=float(new.mean()),
                recent_minus_remote=float(new.mean()-old.mean()),
                remote_greater_fraction=float((dif>0).mean()), tie_fraction=float((dif==0).mean())))
    robust=[r['recent_minus_remote'] for r in summaries if r['n_remote']>=2 and r['n_recent']>=2]
    return dict(paired_people=len(summaries),recent_minus_remote=interval([r['recent_minus_remote'] for r in summaries]),
        remote_greater_fraction=interval([r['remote_greater_fraction'] for r in summaries]),
        tie_fraction=float(np.mean([r['tie_fraction'] for r in summaries])),
        two_each_sensitivity=interval(robust)),summaries

def run(rawdir=None):
    data=ROOT/'data';results=ROOT/'results';data.mkdir(exist_ok=True);results.mkdir(exist_ok=True)
    provenance=json.loads((ROOT/'sources.json').read_text())
    if rawdir:
        for s in provenance['input_files']:
            assert hashlib.sha256((rawdir/s['file']).read_bytes()).hexdigest()==s['sha256'],s['file']
        tr,at=prepare_inner(read_csv(rawdir/'data_original_exp.csv'),'T')
        te,ae=prepare_inner(read_csv(rawdir/'data_replication_exp.csv'),'E')
        cr,ac=prepare_cram(read_csv(rawdir/'cram.csv'))
        for name,rows in [('inner_original.csv',tr),('inner_replication.csv',te),('memory_content.csv',cr)]: write_csv(data/name,rows)
        audit=dict(original=at,replication=ae,cram=ac)
        (data/'sample_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    else:
        tr=read_csv(data/'inner_original.csv');te=read_csv(data/'inner_replication.csv');cr=read_csv(data/'memory_content.csv')
        audit=json.loads((data/'sample_audit.json').read_text())
    main,preds,scores=inner_analysis(tr,te,'dialogic')
    strict,_,_=inner_analysis(tr,te,'strict_dialogic')
    memory,ms=cram_analysis(cr)
    for name,rows in [('predictions.csv',preds),('person_scores.csv',scores),('memory_person_summaries.csv',ms)]: write_csv(results/name,rows)
    summary=dict(protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
        seed=SEED,bootstrap_draws=2000,audit=audit,inner=main,strict_sensitivity=strict,memory=memory)
    (results/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path);args=p.parse_args();run(args.raw_dir)
