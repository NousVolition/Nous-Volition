"""Explicit synthetic encounter rules. No fitted human or language model."""
from dataclasses import dataclass
import math
import re
import numpy as np

LABELS=('Water','Fog','Mist','Gas','Smoke','Clay','Ice')
TASKS=('planning the meal','arranging chairs','checking supplies','writing the notes',
       'tidying the room','coordinating transport','preparing the agenda','setting up the call',
       'sorting shared tools','reviewing the schedule','organizing the files','welcoming visitors')

@dataclass(frozen=True)
class Rule:
    intercept: float=math.log(.2/.8)
    wording: float=0.
    history: float=0.
    retention: float=.8
    input_gain: float=.25

def variants(task,minutes):
    """Same authored propositional record, not independently validated full meaning."""
    return {
      'direct':f'I can give {minutes} minutes to {task}. I will not give more than {minutes} minutes.',
      'courteous':f'Please accept my offer of {minutes} minutes for {task}; my limit is {minutes} minutes.',
      'formal':f'My offer for {task} is limited to {minutes} minutes.',
      'forceful':f'I refuse to give more than {minutes} minutes to {task}; I offer {minutes} minutes.'}

def lexical_marker(text):
    """Chosen literal marker; not a learned rating of politeness or harmfulness."""
    words=re.findall(r"[a-z]+",text.lower())
    pairs=list(zip(words,words[1:]))
    return int(('will','not') in pairs)+int('refuse' in words)-int('please' in words)

def probability(text,context,state,rule):
    z=rule.intercept+context+rule.wording*lexical_marker(text)+rule.history*np.asarray(state)
    return 1/(1+np.exp(-np.clip(z,-700,700)))

def update(state,treatment,rule):
    return rule.retention*np.asarray(state)+rule.input_gain*np.asarray(treatment)

def twin_history(seed,rule,rounds=30,reset_at=None,record_only=False):
    """Forced initial treatments 0/1; identical later text/context/random numbers.

    Restriction is a binary institutional decision W, not distress or wellbeing.
    Later trials use common random numbers for paired numerical comparisons.
    A reset before later round k clears both histories, not the random stream.
    """
    rng=np.random.default_rng(seed)
    noise=rng.uniform(size=rounds)
    context=rng.uniform(-.8,.8,size=rounds)
    text=variants(TASKS[seed%len(TASKS)],20)['formal']
    state=np.array([0.,rule.input_gain])
    rows=[]
    for t in range(rounds):
        if reset_at is not None and t+1==reset_at: state[:]=0
        p=probability(text,context[t],state,rule)
        decision=(noise[t]<p).astype(int)
        rows.append((t+1,*state,*p,*decision))
        state=update(state,np.zeros(2) if record_only else decision,rule)
    return np.asarray(rows,float)

def coefficient_audit(coef,se,reported_or):
    estimated=math.exp(coef)
    # Both the coefficient and printed odds ratio are rounded to two decimals.
    consistent=not (math.exp(coef+.005)<reported_or-.005 or
                    math.exp(coef-.005)>reported_or+.005)
    return dict(odds_ratio=estimated,lower=math.exp(coef-1.96*se),
                upper=math.exp(coef+1.96*se),table_consistent=consistent)
