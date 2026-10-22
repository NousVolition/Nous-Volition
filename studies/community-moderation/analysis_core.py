"""Auditable helpers: semantic retrieval, block episodes and paired summaries."""
import re,html,math,datetime,hashlib
import numpy as np
from scipy.stats import binomtest,binom
from scipy.special import logsumexp

DAY=86400
def digest(s):return hashlib.sha256(str(s).encode('utf-8')).hexdigest()
def epoch(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def tokens(s):return re.findall(r"[\w']+",html.unescape(s).casefold())
def available(s):
    s=s.strip().casefold()
    return bool(s) and not s.startswith(('[deleted]','[removed]')) and s not in ('deleted','removed')
def jaccard(a,b):
    a,b=set(tokens(a)),set(tokens(b));return len(a&b)/len(a|b) if a|b else 0.
def expiry(params,t):
    if not isinstance(params,dict):return None
    e=params.get('expiry');d=str(params.get('duration','')).strip().casefold()
    if e and re.match(r'^\d{4}-',str(e)):
        try:return epoch(e)
        except ValueError:return None
    if str(e).casefold() in ('infinite','indefinite','infinity','never') or d in ('infinite','indefinite','infinity','never'):return math.inf
    m=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(second|minute|hour|day|week)s?',d)
    if m:return t+float(m[1])*{'second':1,'minute':60,'hour':3600,'day':DAY,'week':7*DAY}[m[2]]
    return None
def disruption(s):return bool(re.search(r'personal.?attack|incivil|harass|edit.?war|disrupt',s,re.I))

def episodes(events):
    """Input sorted tuples(time,logid,action,expiry,moderator,reason_flag).
    Return episodes, issues. Unknown durations or orphan modifications disqualify
    the account downstream; never invent expiry or a new episode from reblock.
    """
    out=[];active=None;issues=set()
    for t,i,act,e,mod,reason in sorted(events):
        if active is not None and t>=active['end']:active=None
        if act=='unblock':
            if active is not None:active['end']=min(active['end'],t);active=None
            else:issues.add('orphan_unblock')
            continue
        if e is None or e<=t:
            issues.add('unknown_or_nonpositive_expiry');continue
        if active is None:
            if act=='reblock':issues.add('orphan_reblock');continue
            active={'start':t,'end':e,'initial_duration':e-t,'moderator':mod,'disruption':bool(reason),'logid':i}
            out.append(active)
        else:
            active['end']=e
    return out,issues

def paired_duration(rows,seed=20261021,reps=2000):
    if not rows:return {'n':0}
    rows=sorted(rows)
    x=np.asarray([r[0] for r in rows]);y=np.asarray([r[1] for r in rows]);z=np.log2(y/x)
    rng=np.random.default_rng(seed);boots=[float(np.median(z[rng.integers(0,len(z),len(z))])) for _ in range(reps)]
    longer=int((y>x).sum());shorter=int((y<x).sum());ties=int((y==x).sum())
    non_ties=longer+shorter
    logp=min(0.,float(math.log(2)+logsumexp(binom.logpmf(np.arange(min(longer,shorter)+1),non_ties,.5)))) if non_ties else 0.
    pv=float(binomtest(longer,non_ties).pvalue) if non_ties else 1.
    return {'n':len(rows),'first_median_hours':float(np.median(x)/3600),'second_median_hours':float(np.median(y)/3600),'median_log2_ratio':float(np.median(z)),
            'median_ratio':float(2**np.median(z)),'median_log2_ratio_ci95':np.quantile(boots,[.025,.975]).tolist(),'longer':longer,'shorter':shorter,'equal':ties,
            'sign_test_p':pv if pv else None,'sign_test_log10_p':logp/math.log(10),'seed':seed,'bootstrap_replicates':reps}

def did_bounds(cells):
    """cells= list of four-status rows [Tbefore,Tafter,Cbefore,Cafter].
    Status None remains unknown. Exact logical bounds, not confidence intervals.
    """
    coefs=(-1,1,1,-1);lo=hi=0.
    for row in cells:
        for k,v in zip(coefs,row):
            if v is None:lo+=min(0,k);hi+=max(0,k)
            else:lo+=k*v;hi+=k*v
    return [lo/len(cells),hi/len(cells)] if cells else [None,None]
