"""Complete declarations for one reviewed, byte-pinned real runner."""
from pathlib import Path
import datetime
import hashlib
import json
import math
import sys
P = Path(__file__).resolve().parent
TRUSTED = {
 "gate_worker.py":"0f73c23b45d6f3d806c8cf4b592f7241f2e6a8d8f96bb1e494e6ed7afe2e1d93",
 "manifest_sha256.json":"127f78c467a0356fdaf62b333473c858793c4a451ab98504c2ce00bcd2d346dd",
 "run_contract.json":"cc91253f756681d097245ebe8a338d209b0416af2556dec804bf0b2c9e4ee794",
 "parameter_bounds.json":"50bb21ea6f4764a4d8b87748fd962c6e5c20db7cd20303343f2dd433c4a06180",
 "inheritance_review.json":"160ecc2d1394e7c89f31eef03630117a15f80ca7c6054a7ec27c036f93ca1ed1",
 "notice_baseline.json":"3586a0078346594320335045ac83196a822062fd36e7f1e64ab70c0858a053e9",
}
METADATA={"study","run_id","date","declared_by"}
def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def strict_loads(text):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d: raise ValueError("Duplicate JSON key: "+k)
   d[k]=v
  return d
 def bad(v): raise ValueError("Nonfinite JSON constant: "+v)
 return json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
def strict_json(path):
 return strict_loads(Path(path).read_bytes())
def canonical(value):
 return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":"))
def integrity_errors(root=P):
 root=Path(root);errors=[]
 for name,digest in TRUSTED.items():
  p=root/name
  if not p.is_file() or p.is_symlink() or sha(p)!=digest: errors.append("Trusted file missing or changed: "+name)
 if errors:return errors
 pins=strict_json(root/"manifest_sha256.json")
 if len(pins)!=86:return ["Expected 86 pinned audit files"]
 for name,digest in pins.items():
  p=root/name
  if not p.resolve().is_relative_to(root.resolve()) or not p.is_file() or p.is_symlink() or sha(p)!=digest:
   errors.append("Pinned file missing or changed: "+name)
 return errors
def chain_status(study,root=P):
 # Explicit review supplement, never inferred from absence of keywords.
 return next((r["status"] for r in strict_json(Path(root)/"inheritance_review.json") if r["study"]==study),None)
def check_parameters(parameters,root=P):
 specs=strict_json(Path(root)/"parameter_bounds.json")["parameters"];errors=[]
 if not isinstance(parameters,dict):return ["Parameters must be an object"]
 expected=set(strict_json(Path(root)/"run_contract.json")["cases"][0]["parameters"])
 if set(parameters)!=expected:errors.append("Every solver parameter must be present, with no unknown parameters")
 for name,value in parameters.items():
  if name not in specs:
   errors.append("Unknown parameter: "+name);continue
  s=specs[name]
  if s["kind"]=="choice":
   if value not in s["choices"]:errors.append("Unknown law: "+name)
  elif s["kind"]=="unit_vector":
   if not isinstance(value,list) or len(value)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value) or abs(math.hypot(*value)-1)>1e-9:
    errors.append("Invalid implementation unit direction")
  elif type(value) not in (int,float) or not math.isfinite(value):errors.append("Nonfinite or nonnumeric parameter: "+name)
  else:
   if s["kind"]=="integer" and (type(value) is not int or value%s.get("multiple_of",1)):errors.append("Grid must be an even integer")
   if s.get("min") is not None and (value<s["min"] or (s.get("exclusive_min") and value==s["min"])):errors.append("Below bound: "+name)
   if s.get("max") is not None and (value>s["max"] or (s.get("exclusive_max") and value==s["max"])):errors.append("Above bound: "+name)
 return errors
def validate(manifest,root=P):
 errors=integrity_errors(root)
 if errors:return errors
 contract=strict_json(Path(root)/"run_contract.json")
 if not isinstance(manifest,dict):return ["Manifest must be an object"]
 if set(manifest)!=set(contract)|METADATA:errors.append("Manifest keys must include the complete sealed contract and four metadata fields")
 for key in METADATA:
  v=manifest.get(key)
  if not isinstance(v,str) or not v.strip() or len(v)>200:errors.append("Missing/invalid metadata: "+key)
 try:
  d=manifest.get("date")
  if datetime.date.fromisoformat(d).isoformat()!=d:raise ValueError()
 except (TypeError,ValueError):errors.append("Invalid ISO calendar date")
 if manifest.get("study")!="community-chain-audit":errors.append("This profile belongs to community-chain-audit")
 for key,value in contract.items():
  try:equal=canonical(manifest.get(key))==canonical(value)
  except (TypeError,ValueError,OverflowError):equal=False
  if not equal:errors.append("Declaration differs from reviewed runner contract: "+key)
 if manifest.get("claims_corpus_validation") is not False:errors.append("This numerical fixture cannot claim empirical corpus validation")
 cases=manifest.get("cases")
 if isinstance(cases,list):
  for i,case in enumerate(cases):
   if not isinstance(case,dict):errors.append("Case must be an object");continue
   errors += [f"case {i}: {e}" for e in check_parameters(case.get("parameters"),root)]
 return errors
def main(argv=None):
 argv=sys.argv if argv is None else argv
 if len(argv)!=2:print("Usage: python run_manifest.py manifest.json");return 2
 try:errors=validate(strict_json(argv[1]))
 except (OSError,ValueError,TypeError) as exc:errors=[str(exc)]
 if errors:
  print("Run manifest refused before solver import:\n"+"\n".join("  - "+e for e in errors));return 1
 print("Run manifest accepted: complete sealed numerical fixture; no empirical validation claim.")
 print("Five register rows; 20 added-rule groups; 18 coupled cases; 3 separate board alternatives; 17 source-pinned equation tests.")
 return 0
if __name__=="__main__":sys.exit(main())
