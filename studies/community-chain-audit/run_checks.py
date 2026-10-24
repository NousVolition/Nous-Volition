"""Full coupled PDE verification fixtures; no fitted human predictor."""
from pathlib import Path
import json,hashlib,unittest,io,platform
import numpy as np
from scipy.linalg import expm
import scipy
from audited_field import Field,Parameters,evolve,refinement_is_distinct

P=Path(__file__).resolve().parent
def l2(a,b):
 n=a.shape[-1];m=b.shape[-1];ka=np.rint(np.fft.fftfreq(n)*n).astype(int)
 ix=ka % m;selected=b[:,ix[:,None],ix[None,:]]/m**2
 return float(np.sqrt(np.sum(abs(a/n**2-selected)**2)))
def run():
 results=[];states={};role_difference=[];offset_difference=[]
 for law in ('sharp','tanh','smooth_off'):
  configs=[('n24',24,.001),('n48',48,.001),('n72',72,.001)]
  rows_by={}
  for label,n,dt in configs:
   p=Parameters(n=n,law=law,mu0=.07);f=Field(p);z,_=f.initial(total=.3)
   intervals=[dict(person='synthetic',start=0.,end=.125,utility=1.,role='Smoke',event_ref='fixture:first'),dict(person='synthetic',start=.125,end=.25,utility=-1.,role='Clay',event_ref='fixture:second')]
   z,A,rows=evolve('synthetic',intervals,p,z=z,A=.2,start=0.,initial_state_basis='declared synthetic nonzero prehistory',max_dt=dt)
   states[law+'_'+label]=z;rows_by[label]=rows;results.append(dict(law=law,configuration=label,n=n,rows=rows))
  f=Field(Parameters(n=48,law=law,mu0=.07));z0,_=f.initial(.3)
  z,A,rows=evolve('synthetic',intervals,f.p,z=z0,A=.2,start=0.,initial_state_basis='same synthetic prehistory',max_dt=rows_by['n48'][0]['dt']/2)
  assert refinement_is_distinct(rows_by['n48'],rows)
  states[law+'_half']=z;results.append(dict(law=law,configuration='n48_actual_half',n=48,rows=rows))
  same=[dict(e,role='Clay' if e['role']=='Smoke' else 'Smoke') for e in intervals]
  z2,_,_=evolve('synthetic',same,f.p,z=z0,A=.2,start=0.,initial_state_basis='same synthetic prehistory',max_dt=.001)
  role_difference.append(dict(law=law,maximum=float(abs(z2-states[law+'_n48']).max())))
  shifted=z0.copy();shifted[2,0,0]+=48**2*10
  z3,_,_=evolve('synthetic',intervals,f.p,z=shifted,A=.2,start=0.,initial_state_basis='declared S zero-shift',max_dt=.001)
  z3[2,0,0]-=48**2*10;offset_difference.append(dict(law=law,physical_rms=l2(z3,states[law+'_n48'])) )
 refinements=[dict(law=law,grid24_48=l2(states[law+'_n24'],states[law+'_n48']),grid48_72=l2(states[law+'_n48'],states[law+'_n72']),actual_half_step=l2(states[law+'_n48'],states[law+'_half'])) for law in ('sharp','tanh','smooth_off')]
 for r in refinements:assert r['grid48_72']<r['grid24_48']
 # Alternative board laws, tested as alternatives only, never inserted in corpus.
 # state [A,M,1]; independently exponentiate each constant-input segment.
 def alternative(lam,mu,inputs):
  state=np.array([0.,0.,1.])
  for duration,U in inputs:
   B=np.array([[-lam,0.,U],[1.,-mu,0.],[0.,0.,0.]])
   state=expm(B*duration)@state
  return state[:2].tolist()
 alternatives=dict(A_decay_balanced=alternative(1,0,[(1,1),(1,-1),(38,0)]),A_decay_reversed=alternative(1,0,[(1,-1),(1,1),(38,0)]),S_relaxation_finite_pulse=alternative(0,1,[(1,1),(39,0)]),scope='These two decay equations are board proposals, not the unchanged corpus model.')
 assert abs(alternatives['A_decay_balanced'][1])<1e-12 and abs(alternatives['S_relaxation_finite_pulse'][1]-1)<1e-12
 log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(P),pattern='test_audit.py');t=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 (P/'test_log.txt').write_text(log.getvalue(),encoding='utf-8');assert t.wasSuccessful()
 data=dict(scope='Full-field numerical fixtures; not observations or an empirical two-in-one fit',python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,unit_tests=t.testsRun,full_coupled_runs=18,legacy_sha256=hashlib.sha256((P/'legacy_field.py').read_bytes()).hexdigest(),results=results,refinement=refinements,role_label_differences=role_difference,S_offset_differences=offset_difference,board_alternative_checks=alternatives,max_mass_error=max(abs(r['mass_error']) for c in results for r in c['rows']),max_divergence=max(r['divergence_rms'] for c in results for r in c['rows']))
 (P/'results.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:data[k] for k in ['unit_tests','full_coupled_runs','refinement','board_alternative_checks','max_mass_error','max_divergence']},indent=2))
if __name__=='__main__':run()
