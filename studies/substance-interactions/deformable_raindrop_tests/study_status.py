"""Account for completed, interrupted and unstarted cases without running CFD."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent

def study_status():
    context=json.loads((P/'release_context.json').read_text())
    planned=set()
    for file in ['run_design.json','refined_run_design.json']:
        planned.update(name for name,_ in json.loads((P/file).read_text()))
    cases=[]
    for name in sorted(planned):
        meta=P/'flow'/name/'metadata.json'
        if meta.exists():
            state=json.loads(meta.read_text())['status']
        elif name in context['interrupted_cases']:
            state='interrupted_by_user_no_final_record'
        else:
            state='not_run'
        cases.append(dict(name=name,status=state,description=context['unfinished_checks'].get(name,'')))
    completed=sum(x['status']=='completed' for x in cases)
    unfinished=[x for x in cases if x['status']!='completed']
    return dict(publication_date_local=context['publication_date_local'],
        status='interim_partial_study' if unfinished else 'all_planned_cases_completed',
        planned=len(cases),completed=completed,started=sum(x['status']!='not_run' for x in cases),
        all_planned_cases_completed=not unfinished,unfinished=unfinished,cases=cases)

if __name__=='__main__':
    result=study_status()
    (P/'study_status.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
