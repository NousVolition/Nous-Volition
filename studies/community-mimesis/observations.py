"""Explicit measurement procedures, NOT equations from the user's corpus."""
import collections,hashlib,html,json,re,zipfile
from pathlib import Path

DELI_SHA='ad24289c4d75593e22fb640fec55186dbb6a10b2cba61d7f854aba04df8c208d'
CGA_SHA='eb5b7dc7a043c9ec9078d8ca0cc43c0abc58f41d30d09a32ff79dad6643d885b'
STOP=set('a an the and or to of in on for by is are was were be been being i you he she it we they this that these those with as at if then than so but not no do does did have has had my your our their its me us them what which who how why when can could would should will just all some any one'.split())
def digest(s):return hashlib.sha256(str(s).encode()).hexdigest()
def file_hash(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read_public_cga(path):
    import csv
    rows=[]
    with open(path,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append({'conversation_hash':r['conversation_hash'],'pair_hash':r['pair_hash'],'cluster':r['cluster_hash'],
                         'removed':int(r['removed']), 'primary':{k:int(r['primary_'+k]) for k in ['any','third','reciprocal']},
                         'quotes':{'any':int(r['quotes_any'])},'fourgram':{'any':int(r['fourgram_any'])},
                         'cross_branch_placebo':int(r['cross_branch_placebo'])})
    return rows
def valid_text(x):return isinstance(x,str) and x.strip().lower() not in ('nan','','[deleted]','[removed]')
def card_set(text):
    if not isinstance(text,str):return None
    toks=text.strip().split(',')
    if not toks or not all(re.fullmatch(r'[A-Z]|[0-9]+',t.strip()) for t in toks):return None
    toks=[t.strip() for t in toks]
    if len(set(toks))!=len(toks):return None
    return tuple(sorted(toks))
def correct(cards):
    return len(cards)==2 and sum(x in 'AEIOU' for x in cards)==1 and sum(x.isdigit() and int(x)%2==1 for x in cards)==1
def phrases(text,n=3,include_quotes=False):
    if not valid_text(text):return set()
    text=html.unescape(text)
    text=re.sub(r'https?://\S+','<SPLIT>',text)
    if not include_quotes:
        text=re.sub(r'(?m)^\s*>.*$','<SPLIT>',text)
        text=re.sub(r'"[^"\n]*"|“[^”\n]*”','<SPLIT>',text)
    found=set()
    for chunk in text.split('<SPLIT>'):
        words=re.findall(r"[a-z]+(?:'[a-z]+)?",chunk.lower())
        found|={tuple(words[i:i+n]) for i in range(len(words)-n+1) if any(w not in STOP for w in words[i:i+n])}
    return found
def reuse_features(rows,n=3,include_quotes=False):
    own=collections.defaultdict(set);other=[];marks=[];shared=[]
    for r in rows:
        p=phrases(r['text'],n,include_quotes);s=r['speaker']
        prior=set().union(*(z for a,z in other if a!=s)) if other else set()
        hit=(p-own[s])&prior;shared.append(sorted(' '.join(h) for h in hit));marks.append(bool(hit))
        own[s]|=p;other.append((s,p))
    reciprocal=len(rows)==3 and rows[0]['speaker']==rows[2]['speaker']!=rows[1]['speaker'] and all(marks[1:])
    return {'any':int(any(marks[1:])),'third':int(marks[2]) if len(marks)>2 else 0,'reciprocal':int(reciprocal),'phrases':shared}

def load_deli(path):
    if file_hash(path)!=DELI_SHA:raise ValueError('DeliData source changed')
    with zipfile.ZipFile(path) as z:rs=[json.loads(l) for l in z.open('deli-corpus/utterances.jsonl')]
    if len({r['id'] for r in rs})!=len(rs):raise ValueError('Duplicate message ids')
    by=collections.defaultdict(list)
    for r in rs:by[r['conversation_id']].append(r)
    transitions=[];audit={};cnt=collections.Counter()
    for group, rows in by.items():
        ids={r['id'] for r in rows};seen=set()
        for r in rows:
            if r['reply-to'] in ids and r['reply-to'] not in seen:raise ValueError('Archive not in reply order')
            seen.add(r['id'])
        voc=set(x for r in rows if r['meta']['message_type']=='SUBMIT' and (cs:=card_set(r['meta']['original_text'])) is not None for x in cs)
        full=len(voc)==4 and sum(x in 'AEIOU' for x in voc)==1 and sum(x.isalpha() and x not in 'AEIOU' for x in voc)==1 and sum(x.isdigit() and int(x)%2 for x in voc)==1 and sum(x.isdigit() and int(x)%2==0 for x in voc)==1
        last={}
        for t,r in enumerate(rows):
            cnt[r['meta']['message_type']]+=1
            if r['meta']['message_type']!='SUBMIT':continue
            cs=card_set(r['meta']['original_text'])
            if cs is None:cnt['unparsed_submissions']+=1;continue
            speaker=r['speaker']
            if speaker not in last:last[speaker]=(t,cs);cnt['first_observed_submission']+=1;continue
            prev,old=last[speaker]
            if cs==old:cnt['unchanged_submissions']+=1;continue
            candidates=[]
            for j in range(prev+1,t):
                s=rows[j];m=s['meta']
                if s['speaker']==speaker or m['message_type']!='MESSAGE':continue
                if m['annotation_type']!='Non-probing-deliberation' or 'complete_solution' not in str(m['annotation_additional']):continue
                text=m['original_text']
                if not valid_text(text):continue
                toks=set(re.findall(r'(?<!\w)(?:[A-Z]|[0-9]+)(?!\w)',text))&voc
                if tuple(sorted(toks))==cs:candidates.append(j)
            h=digest(group+'|'+str(t));gh=digest(group)
            rec={'event_hash':h,'group_hash':gh,'before':list(old),'after':list(cs),'before_correct':int(correct(old)),
                 'after_correct':int(correct(cs)),'delta':int(correct(cs))-int(correct(old)),
                 'candidate':bool(candidates),'full_card_vocabulary':bool(full),'message_gap':t-prev}
            transitions.append(rec)
            if candidates:
                aliases={s:i for i,s in enumerate(dict.fromkeys(x['speaker'] for x in rows))}
                audit[h]={'event_hash':h,'group_hash':gh,'previous_selection':list(old),'later_selection':list(cs),'proposer_turns':candidates,
                          'turns':[{'turn':j,'speaker':'participant_'+str(aliases[rows[j]['speaker']]),'kind':rows[j]['meta']['message_type'],
                           'text':rows[j]['meta']['original_text']} for j in range(max(0,prev-2),min(len(rows),t+2))]}
            last[speaker]=(t,cs)
    chosen=[];groups=set()
    for h in sorted(audit):
        if audit[h]['group_hash'] not in groups:chosen.append(audit[h]);groups.add(audit[h]['group_hash'])
        if len(chosen)==16:break
    return transitions,chosen,dict(cnt)|{'groups':len(by),'archive_records':len(rs)}

def load_cga(path):
    if file_hash(path)!=CGA_SHA:raise ValueError('CGA source changed')
    with zipfile.ZipFile(path) as z:
        pre='conversations-gone-awry-cmv-corpus/'
        cv=json.loads(z.read(pre+'conversations.json'))
        by=collections.defaultdict(list)
        for l in z.open(pre+'utterances.jsonl'):
            r=json.loads(l);r['meta'].pop('parsed',None);by[r['conversation_id']].append(r)
    allrows={};early={};pairs=collections.defaultdict(list)
    for c,rows in by.items():
        ids={r['id']:r for r in rows};parents={r['reply-to'] for r in rows}
        leaves=[r for r in rows if r['id'] not in parents]
        if len(leaves)!=1:raise ValueError('Nonlinear source path')
        ordered=[];r=leaves[0]
        while r is not None:
            ordered.append(r);r=ids.get(r['reply-to'])
            if len(ordered)>len(rows):raise ValueError('Cycle')
        ordered.reverse()
        if len(ordered)!=len(rows):raise ValueError('Disconnected path')
        if len(ordered)<4 or any(not valid_text(r['text']) or not r['speaker'] for r in ordered[:3]):continue
        first=ordered[:3];h=digest(c)
        topics=[]
        for r in first:
            m=re.search(r'/comments/([^/]+)/',str(r['meta'].get('permalink','')))
            if m:topics.append(m.group(1))
        cluster=digest(topics[0]) if topics else None
        partner=cv[c]['meta']['pair_id']
        if partner not in cv or cv[partner]['meta']['pair_id']!=c:raise ValueError('Nonreciprocal source match')
        pairkey='|'.join(sorted((c,partner)))
        allrows[h]={'conversation_hash':h,'pair':pairkey,'topic':cluster,
                    'removed':int(cv[c]['meta']['has_removed_comment']),
                    **{name:reuse_features(first,n,quote) for name,n,quote in [('primary',3,False),('quotes',3,True),('fourgram',4,False)]}}
        early[h]=first;pairs[pairkey].append(h)
    output=[];audit={};eligible=0
    for pair,hs in pairs.items():
        if len(hs)!=2 or {allrows[h]['removed'] for h in hs}!={0,1}:continue
        eligible+=1
        topics={allrows[h]['topic'] for h in hs if allrows[h]['topic'] is not None}
        if len(topics)>1:raise ValueError('Matched branches disagree on source topic')
        cluster=next(iter(topics)) if topics else digest(pair)
        for h,other in [hs,hs[::-1]]:
            row=allrows[h];rs=early[h];os=early[other]
            row['cluster']=cluster
            prior=set().union(*(phrases(r['text']) for r in os[:2] if r['speaker']!=rs[2]['speaker']))
            own=set().union(*(phrases(r['text']) for r in rs[:2] if r['speaker']==rs[2]['speaker']))
            row['cross_branch_placebo']=int(bool((phrases(rs[2]['text'])-own)&prior))
            row['pair_hash']=digest(pair);row.pop('pair')
            output.append(row)
            if row['primary']['any']:
                alias={s:i for i,s in enumerate(dict.fromkeys(r['speaker'] for r in rs))}
                audit[h]={'conversation_hash':h,'phrases':row['primary']['phrases'],
                          'turns':[{'speaker':'participant_'+str(alias[r['speaker']]),'text':r['text']} for r in rs]}
    chosen=[];chosenpairs=set();pairslookup={r['conversation_hash']:r['pair_hash'] for r in output}
    for h in sorted(audit):
        if pairslookup[h] not in chosenpairs:chosen.append(audit[h]);chosenpairs.add(pairslookup[h])
        if len(chosen)==12:break
    return output,chosen,{'source_conversations':len(by),'eligible_pairs':eligible,'topic_available':sum(r['topic'] is not None for r in output)}

def prepare(deli,cga,private,out):
    private.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
    dr,da,dc=load_deli(deli);cr,ca,cc=load_cga(cga)
    for name,obj in [('deli_rows',dr),('cga_rows',cr),('deli_audit_blind',da),('cga_audit_blind',ca)]:
        (private/(name+'.json')).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
    receipt={'protocol_sha256':file_hash(Path(__file__).with_name('PROTOCOL.md')),'deli_source_sha256':DELI_SHA,'cga_source_sha256':CGA_SHA,
             'deli_schema':dc,'cga_eligibility':cc,'deli_audit_ids':[r['event_hash'] for r in da],'cga_audit_ids':[r['conversation_hash'] for r in ca],
             'blinded_inputs_sha256':{name:file_hash(private/(name+'.json')) for name in ['deli_audit_blind','cga_audit_blind']}}
    (out/'selection.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({'deli_schema':dc,'cga_eligibility':cc,'audit_sizes':[len(da),len(ca)]}))

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--deli',type=Path,required=True);a.add_argument('--cga',type=Path,required=True);a.add_argument('--private',type=Path,required=True);a.add_argument('--out',type=Path,default=Path(__file__).with_name('results'));v=a.parse_args()
    prepare(v.deli,v.cga,v.private,v.out)
