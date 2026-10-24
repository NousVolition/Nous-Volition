"""Reject cross-person histories, dangling links and invented form measurements."""
FORM_KEYS={'Water','Fog','Wind','Mist','D2O','H2O2'}
DESCRIPTORS={'perceived_balance','calm','disturbance','recalled_content','retrieval_clarity',
             'event_age','felt_temporal_distance','unspoken_assumption','endorsement',
             'specified_small_change','observed_consequence'}

def validate(data):
    histories={h['id']:h for h in data['history']}
    if len(histories)!=len(data['history']):raise ValueError('Duplicate history ID')
    for episode in data['episodes']:
        person=episode['person_id'];nodes={n['id']:n for n in episode['nodes']}
        if len(nodes)!=len(episode['nodes']):raise ValueError('Duplicate node ID')
        if set(episode['forms'])!=FORM_KEYS:raise ValueError('Missing form status')
        if set(episode['descriptors'])!=DESCRIPTORS:raise ValueError('Missing observation field')
        for n in nodes.values():
            if not set(n['operations'])<= {'Smoke','Clay'}:raise ValueError('Unknown operation')
            for ref in n['history_refs']:
                if ref not in histories:raise ValueError('Unknown history')
                if histories[ref]['person_id']!=person:raise ValueError('Cross-person history')
        for edge in episode['edges']:
            if edge['from'] not in nodes or edge['to'] not in nodes:raise ValueError('Dangling edge')
            if not edge.get('status'):raise ValueError('Unattributed relation')
        for form,key in [('Water','perceived_balance'),('Mist','unspoken_assumption'),('D2O','specified_small_change')]:
            if episode['forms'][form]=='observed' and episode['descriptors'][key] is None:
                raise ValueError('Unmeasured form marked observed')
    return dict(episodes=len(data['episodes']),people=len({e['person_id'] for e in data['episodes']}),
                history_references=len(histories),nodes=sum(len(e['nodes']) for e in data['episodes']))
