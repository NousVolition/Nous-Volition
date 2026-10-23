from pathlib import Path
import argparse,collections,gzip,hashlib,itertools,json,math,re
import numpy as np

P=Path(__file__).parent;R=P/'results'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def normalized(s):return ' '.join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",s.lower()))
def agreement(votes):
    pairs=list(itertools.combinations(votes,2))
    return sum(not x.get('unidentifiable') and not y.get('unidentifiable') and set(x['referents'])==set(y['referents']) for x,y in pairs)/len(pairs)
def canonical(r):return r.split('_',2)[2]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,required=True);args=ap.parse_args();raw=args.raw;R.mkdir(exist_ok=True)
    manifest=json.loads((raw/'source_manifest.json').read_text())
    for f in manifest['files']:
        if hashlib.sha256((raw/f['name']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Source changed '+f['name'])
    (P/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    transcripts=json.loads((raw/'final_transcripts.json').read_text());marks=json.loads((raw/'markable_annotation.json').read_text());agg=json.loads((raw/'aggregated_referent_annotation.json').read_text());votes=json.loads((raw/'referent_annotation.json').read_text())
    counts=collections.Counter();pairs=[];overlaps=[];episodes=[];audit=[]
    scenarios=sorted({c['scenario_uuid'] for c in transcripts},key=lambda s:sha('reference-field-v1|'+s));cut=int(.7*len(scenarios));train=set(scenarios[:cut])
    for c in transcripts:
        key=c['uuid'];counts['source_dialogues']+=1
        if key not in marks:counts['not_annotated']+=1;continue
        counts['annotated_dialogues']+=1
        if 'admin' in votes[key]:counts['admin_dialogues_excluded']+=1;continue
        messages=[e for e in c['events'] if e['action']=='message'];text=marks[key]['text'];lines=list(re.finditer(r'(?m)^([01]): ',text))
        if len(messages)!=len(lines) or any(e['agent']!=int(l.group(1)) for e,l in zip(messages,lines)):counts['alignment_failure']+=1;continue
        times=[float(e['time']) for e in messages]
        if any(a>=b for a,b in zip(times,times[1:])):counts['time_failure']+=1;continue
        counts['usable_dialogues']+=1;starts=[l.start() for l in lines];line_marks=collections.defaultdict(list);previous={};previous_word={}
        for m in sorted(marks[key]['markables'],key=lambda x:x['start']):
            counts['markables_considered']+=1;mid=m['markable_id'];g=agg[key].get(mid);worker=[v[mid] for k,v in votes[key].items() if k.startswith('MT_') and mid in v]
            if m['generic'] or g is None or g.get('ambiguous',False) or g.get('unidentifiable',False) or not g['referents']:counts['nonconcrete_or_uncertain_excluded']+=1;continue
            if len(worker)<3:counts['fewer_than_three_votes_excluded']+=1;continue
            refs=tuple(sorted(g['referents']));line=int(np.searchsorted(starts,m['start'],side='right')-1);speaker=m['speaker']
            if any(int(r.split('_')[1])!=speaker for r in refs) or speaker!=messages[line]['agent']:raise ValueError('Wrong perspective')
            if text[m['start']:m['end']]!=m['text']:raise ValueError('Bad text span')
            a=agreement(worker);w=normalized(m['text']);counts['retained_markables']+=1
            rec=dict(dialogue=sha(key),scenario=sha(c['scenario_uuid']),speaker=speaker,line=line,time=times[line],refs=refs,agreement=a,wording=w,mark=sha(key+'|'+mid))
            line_marks[line].append(rec);old=previous.get((speaker,refs))
            if old is not None and old['line']!=line:
                pairs.append(dict(dialogue=sha(key),pair=sha(old['mark']+'|'+rec['mark']),changed_wording=w!=old['wording'],before=old['agreement'],after=a,delta=a-old['agreement'],gap_seconds=times[line]-old['time'],reference_count=len(refs)))
                audit.append(dict(pair=pairs[-1]['pair'],before=old['wording'],after=w,refs=list(refs),dialogue=sha(key),same_reference=True))
            previous[speaker,refs]=rec
            ow=previous_word.get((speaker,w))
            if ow is not None and ow['line']!=line:
                counts['repeated_wording_comparisons']+=1;counts['repeated_wording_changed_referent']+=ow['refs']!=refs
            previous_word[speaker,w]=rec
        utter=[]
        for line,rr in sorted(line_marks.items()):
            refs=sorted(set(r for item in rr for r in item['refs']));speaker=rr[0]['speaker'];kb={str(o['id']):o for o in c['scenario']['kbs'][speaker]}
            points=[[kb[canonical(r)]['x']/430,kb[canonical(r)]['y']/430] for r in refs]
            utter.append(dict(line=line,speaker=speaker,t=times[line],refs=refs,points=points,U=float(np.mean([r['agreement'] for r in rr]))))
        for a,b in zip(utter,utter[1:]):
            if a['speaker']==b['speaker']:continue
            ar={canonical(r) for r in a['refs']};br={canonical(r) for r in b['refs']}
            overlaps.append(dict(dialogue=sha(key),gap_seconds=b['t']-a['t'],jaccard=len(ar&br)/len(ar|br),same_referents=ar==br))
        for speaker in (0,1):
            uu=[u for u in utter if u['speaker']==speaker]
            if len(uu)<3:counts['speaker_sequences_too_short']+=1;continue
            uu=uu[:3];dt=[(b['t']-a['t'])/60 for a,b in zip(uu,uu[1:])]
            if any(x<=0 or x>2 for x in dt):counts['episode_interval_excluded']+=1;continue
            episodes.append(dict(case=sha(key+'|'+str(speaker)),dialogue=sha(key),scenario=sha(c['scenario_uuid']),split='train' if c['scenario_uuid'] in train else 'evaluation',dt=dt,points=[u['points'] for u in uu],U=[u['U'] for u in uu],counts=[len(u['refs']) for u in uu]))
    chosen=[]
    for split in ['train','evaluation']:
        seen=set()
        for e in sorted((e for e in episodes if e['split']==split),key=lambda e:e['case']):
            if e['scenario'] in seen:continue
            chosen.append(e);seen.add(e['scenario'])
            if len(seen)==64:break
        if len(seen)!=64:raise ValueError('Insufficient fixed-size pilot')
    (R/'episodes.json').write_text(json.dumps(chosen,separators=(',',':'))+'\n')
    for name,rows in [('wording_pairs',pairs),('interaction_overlaps',overlaps),('eligible_selection',[{k:e[k] for k in ['case','dialogue','scenario','split']} for e in episodes])]:
        (R/(name+'.json.gz')).write_bytes(gzip.compress((json.dumps(rows,separators=(',',':'))+'\n').encode(),mtime=0))
    counts.update(eligible_episodes=len(episodes),primary_pilot_episodes=len(chosen),wording_pairs=len(pairs),cross_speaker_transitions=len(overlaps),source_scenarios=len(scenarios),training_scenario_assignment=cut)
    (R/'accounting.json').write_text(json.dumps(dict(counts),indent=2)+'\n')
    # Original words remain private. Fixed-hash inspection sample is not new semantic annotation.
    (raw/'wording_inspection.json').write_text(json.dumps(sorted(audit,key=lambda r:r['pair'])[:12],indent=2)+'\n')
    (raw/'all_eligible_episodes.json').write_text(json.dumps(episodes,separators=(',',':'))+'\n')
    print(json.dumps(dict(counts),indent=2))
if __name__=='__main__':main()
