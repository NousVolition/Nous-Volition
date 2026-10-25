"""Observe, without replacing functions, the byte-identical run_checks.py."""
from pathlib import Path
from dataclasses import asdict
import json, runpy, sys
import numpy as np
def main():
 audit=Path(sys.argv[1]).resolve()
 contract=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
 trace_path=Path(sys.argv[3]);expected=contract["cases"]
 trace={"coupled_cases":[],"board_alternatives":[],"model_functions_replaced":False}
 sys.path.insert(0,str(audit))
 runner=str(audit/"run_checks.py");field=str(audit/"audited_field.py");active={}
 def profile(frame,event,arg):
  filename=frame.f_code.co_filename
  if filename==runner and frame.f_code.co_name=="run" and event=="call":
   (audit.parent/"runner_started.json").write_text('{"real_run_checks_started": true}\n',encoding="utf-8")
  if filename==field and frame.f_code.co_name=="evolve" and frame.f_back and frame.f_back.f_code.co_filename==runner:
   if event=="call":
    i=len(trace["coupled_cases"])
    if i>=len(expected):raise RuntimeError("Undeclared coupled case")
    e=expected[i];v=frame.f_locals;params=asdict(v["p"]);params["direction"]=list(params["direction"])
    if params!=e["parameters"]:raise RuntimeError("Observed solver parameter drift")
    for key in ("person","intervals","max_dt","initial_state_basis"):
     if v[key]!=e[key]:raise RuntimeError("Observed case drift: "+key)
    init=e["initial"]
    if v["A"]!=init["A"] or v["start"]!=init["start"]:raise RuntimeError("History drift")
    z=v["z"];n=params["n"]
    if z.shape!=(3,n,n):raise RuntimeError("Initial field shape drift")
    x,y=np.meshgrid(2*np.pi*np.arange(n)/n,2*np.pi*np.arange(n)/n,indexing="ij")
    wanted=np.array([init["speed"]*np.sin(x)*np.cos(y),-init["speed"]*np.cos(x)*np.sin(y),
     np.full_like(x,init["total"]+init["offset"])+init["texture"]*np.cos(x)*np.cos(y)])
    physical=np.fft.ifft2(z,axes=(-2,-1));error=float(abs(physical-wanted).max())
    if error>1e-12:raise RuntimeError("Initial field differs from declared shape")
    row=dict(case_id=e["case_id"],parameters=params,initial_field_max_error=error,A_start=v["A"],
     initial_mean_S=float(physical[2].real.mean()),max_dt=v["max_dt"],intervals=v["intervals"],completed=False)
    trace["coupled_cases"].append(row);active[id(frame)]=row
   elif event=="return":
    row=active.pop(id(frame))
    if arg is None:raise RuntimeError("Evolution did not return")
    row.update(completed=True,A_end=float(arg[1]),rows=arg[2])
  if filename==runner and frame.f_code.co_name=="alternative" and event=="call":
   v=frame.f_locals;i=len(trace["board_alternatives"])
   if i>=len(contract["board_alternatives"]):raise RuntimeError("Undeclared alternative")
   e=contract["board_alternatives"][i]
   actual=dict(lam=v["lam"],mu=v["mu"],inputs=[list(x) for x in v["inputs"]])
   if actual!={k:e[k] for k in actual}:raise RuntimeError("Alternative equation fixture drift")
   trace["board_alternatives"].append(dict(name=e["name"],**actual))
 try:
  sys.setprofile(profile);runpy.run_path(runner,run_name="__main__");sys.setprofile(None)
  if len(trace["coupled_cases"])!=18 or not all(r["completed"] for r in trace["coupled_cases"]):raise RuntimeError("Missing completed coupled cases")
  if len(trace["board_alternatives"])!=3:raise RuntimeError("Missing alternative checks")
  trace["success"]=True
 except BaseException as exc:
  sys.setprofile(None);trace.update(success=False,error=repr(exc));raise
 finally:
  trace_path.write_text(json.dumps(trace,indent=2,allow_nan=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()

