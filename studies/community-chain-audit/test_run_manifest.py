"""Regression checks use the real gate CLI and real files; no mocks."""
import sys
if __name__ == "__main__":
 if not (sys.flags.isolated and sys.flags.no_site):
  raise SystemExit("Use python -I -S test_run_manifest.py -v")
 sys.dont_write_bytecode = True
 from pathlib import Path
 import types
 for name in ("run_manifest","gated_run"):
  path=Path(__file__).resolve().with_name(name+".py")
  module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
  exec(compile(path.read_bytes(),str(path),"exec"),module.__dict__)
from pathlib import Path
import copy, importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest
from run_manifest import P, TRUSTED, canonical, chain_status, check_parameters, integrity_errors, strict_json, validate
from gated_run import run
ROOT=P.parents[1]
EXAMPLE=strict_json(P/"run_manifest.example.json")
class Gate(unittest.TestCase):
 def setUp(self): self.m=copy.deepcopy(EXAMPLE)
 def test_complete_example(self): self.assertEqual(validate(self.m),[])
 def test_missing_and_extra_fields(self):
  for key in self.m:
   m=copy.deepcopy(self.m);del m[key]
   with self.subTest(key=key):self.assertTrue(validate(m))
  self.m["invented"]=1;self.assertTrue(validate(self.m))
 def test_no_additions_or_false_validation(self):
  for key,value in (("added_rules",[]),("inherits",[]),("claims_corpus_validation",True),("claims_corpus_validation",0)):
   m=copy.deepcopy(self.m);m[key]=value
   with self.subTest(key=key):self.assertTrue(validate(m))
 def test_every_rule_and_inheritance_required(self):
  for i in range(20):
   m=copy.deepcopy(self.m);m["added_rules"].pop(i);self.assertTrue(validate(m))
  self.m["inherits"][0]["status"]="corpus";self.assertTrue(validate(self.m))
 def test_unknown_claimed_rows(self):
  self.m["register_rows"].append("Architecture");self.assertTrue(validate(self.m))
 def test_all_numeric_parameters_required(self):
  for key in self.m["cases"][0]["parameters"]:
   m=copy.deepcopy(self.m);del m["cases"][0]["parameters"][key]
   with self.subTest(key=key):self.assertTrue(validate(m))
 def test_gradient_delta_grid_and_coefficient_drift(self):
  for k,v in (("gradient_law","regularized"),("delta",.2),("n",96),("nu",.9)):
   m=copy.deepcopy(self.m);m["cases"][0]["parameters"][k]=v
   with self.subTest(key=k):self.assertTrue(validate(m))
 def test_grid_implementation_bounds(self):
  for n in (8,25,24.0,True):
   p=copy.deepcopy(self.m["cases"][0]["parameters"]);p["n"]=n
   with self.subTest(n=n):self.assertTrue(check_parameters(p))
 def test_coefficient_bounds_and_choice(self):
  for k,v in (("nu",0),("rho",0),("sigma",-1),("epsilon",0),("delta",0),("diffusivity",-1),
              ("mu0",0),("h",0),("direction",[1.,1.]),("law","invented"),("nu",float("nan"))):
   p=copy.deepcopy(self.m["cases"][0]["parameters"]);p[k]=v
   with self.subTest(key=k,value=v):self.assertTrue(check_parameters(p))
 def test_offset_texture_speed_history_intervals_required(self):
  for key in ("offset","texture","speed","A","start","total"):
   m=copy.deepcopy(self.m);m["cases"][-1]["initial"][key]=999
   with self.subTest(key=key):self.assertTrue(validate(m))
  self.m["cases"][0]["intervals"][0]["utility"]=0;self.assertTrue(validate(self.m))
 def test_case_removal_order_and_alternatives(self):
  for key in ("cases","board_alternatives","verification_program","numeric_literals"):
   m=copy.deepcopy(self.m);m[key]=[]
   with self.subTest(key=key):self.assertTrue(validate(m))
  self.m["cases"].reverse();self.assertTrue(validate(self.m))
 def test_date_and_wrong_types(self):
  for value in ("2026-99-99",None,3,"20261024"):
   m=copy.deepcopy(self.m);m["date"]=value
   with self.subTest(value=value):self.assertTrue(validate(m))
  for value in (None,[],5):
   with self.subTest(value=value):self.assertTrue(validate(value))
 def test_explicit_statuses_not_corpus_guess(self):
  for name in ("isfog_pile_tests","community_measured_inner_experience","community_full_field"):
   self.assertNotEqual(chain_status(name),"corpus")
  self.assertIsNone(chain_status("unknown"))
 def test_signed_mass_is_not_a_corpus_positivity_rule(self):
  b=strict_json(P/"parameter_bounds.json")["parameters"]
  self.assertIsNone(b["initial_total"]["min"]);self.assertEqual(b["initial_total"]["source"],"fixture")
  self.assertEqual(b["direction"]["source"],"fixture")
 def test_no_solver_import_on_gate_import(self):
  script="import gated_run,sys; assert not any(x in sys.modules for x in ('run_checks','audited_field','legacy_field'))"
  r=subprocess.run([sys.executable,"-B","-c",script],cwd=P,capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr)
 def test_real_cli_refuses_bad_declarations_without_output(self):
  changes=[("added_rules",[]),("inherits",[]),("claims_corpus_validation",True),("cases",[])]
  with tempfile.TemporaryDirectory() as d:
   d=Path(d)
   for i,(key,value) in enumerate(changes):
    m=copy.deepcopy(self.m);m[key]=value;f=d/f"bad{i}.json";f.write_text(json.dumps(m),encoding="utf-8")
    out=d/f"out{i}"
    r=subprocess.run([sys.executable,"-I","-S","-B",str(P/"gated_run.py"),str(f),"--output",str(out)],capture_output=True,text=True)
    self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertFalse(out.exists())
 def test_duplicate_keys_and_nonfinite_json_refused(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"bad.json"
   for text in ('{"x":1,"x":2}','{"x":NaN}'):
    f.write_text(text)
    with self.assertRaises(ValueError):strict_json(f)
 def test_changed_pinned_runner_refused_before_run(self):
  with tempfile.TemporaryDirectory() as d:
   clone=Path(d)/"source";shutil.copytree(P,clone,ignore=shutil.ignore_patterns("__pycache__","gate_evidence"))
   source=clone/"run_checks.py";original=source.read_bytes()
   for before,after in ((b"('n24',24,.001)",b"('n24',96,.001)"),
                        (b"Parameters(n=n,law=law,mu0=.07)",b"Parameters(n=n,law=law,mu0=.07,nu=.9)")):
    source.write_bytes(original.replace(before,after));out=Path(d)/"output"
    r=subprocess.run([sys.executable,"-I","-S","-B",str(clone/"gated_run.py"),str(clone/"run_manifest.example.json"),"--output",str(out)],capture_output=True,text=True)
    self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertIn("run_checks.py",r.stdout);self.assertFalse(out.exists())
 def test_changed_contract_or_trust_manifest_refused(self):
  with tempfile.TemporaryDirectory() as d:
   clone=Path(d)/"source";shutil.copytree(P,clone,ignore=shutil.ignore_patterns("__pycache__","gate_evidence"))
   for name in TRUSTED:
    p=clone/name;before=p.read_bytes();p.write_bytes(before+b" ")
    self.assertTrue(integrity_errors(clone));p.write_bytes(before)
 def test_existing_output_and_audit_output_refused(self):
  with tempfile.TemporaryDirectory() as d:
   for output in (Path(d),P/"new-output"):
    r=subprocess.run([sys.executable,"-I","-S","-B",str(P/"gated_run.py"),str(P/"run_manifest.example.json"),"--output",str(output)],capture_output=True,text=True)
    self.assertEqual(r.returncode,1,r.stdout+r.stderr)
    self.assertIn("Output must be a new directory",r.stdout)
  self.assertFalse((P/"new-output").exists())
 def test_original_86_still_unchanged(self):self.assertEqual(integrity_errors(),[])
 def test_ci_uses_gate_before_real_runner(self):
  workflow=(ROOT/".github/workflows/blank.yml").read_text(encoding="utf-8")
  job=workflow[workflow.index("  corpus-chain-audit-checks:"):]
  self.assertNotIn("python run_checks.py",job)
  self.assertNotIn("python -m unittest test_audit.py",job)
  self.assertLess(job.index("python -I -S run_manifest.py"),job.index("python -I -S gated_run.py"))
  self.assertLess(job.index("python -I -S gated_run.py"),job.index("python -I -S test_fresh_outputs.py"))
  self.assertIn("python -I -S test_parent_launch.py",job)
  for name in ("run_context.json","runner_started.json","worker_completion.json","fresh_output_regressions.json"):
   self.assertIn(name,job)
  self.assertIn("python studies/community-chain-audit/verify.py",job)
class WorkerFreshness(unittest.TestCase):
 def prepare(self, directory):
  from gated_run import prepare_run
  output=Path(directory)/"new-run"
  context,contract,payload=prepare_run(P/"run_manifest.example.json",output)
  return output,context,contract,payload
 def launch_worker(self, output, payload):
  return subprocess.run([sys.executable,"-I","-S","-B","-",str(output/"audit-copy"),str(output/"run_context.json")],
                        input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=output/"audit-copy")
 def test_checked_worker_payload_and_no_archived_results(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   out,context,contract,payload=self.prepare(d)
   self.assertEqual(hashlib.sha256(payload).hexdigest(),TRUSTED["gate_worker.py"])
   self.assertEqual(context["worker_sha256"],TRUSTED["gate_worker.py"])
   self.assertFalse((out/"audit-copy/results.json").exists())
   self.assertFalse((out/"audit-copy/test_log.txt").exists())
   self.assertEqual(len(context["input_hashes"]),85)
   self.assertEqual(len(context["run_nonce"]),64)
 def test_distinct_run_nonces_and_exact_declaration_bytes(self):
  from gated_run import prepare_run
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/"a";b=Path(d)/"b"
   ca,_,_=prepare_run(P/"run_manifest.example.json",a)
   cb,_,_=prepare_run(P/"run_manifest.example.json",b)
   self.assertNotEqual(ca["run_nonce"],cb["run_nonce"])
   self.assertEqual((a/"declaration.json").read_bytes(),(P/"run_manifest.example.json").read_bytes())
 def test_original_fake_worker_exploit_refused_before_launch(self):
  with tempfile.TemporaryDirectory() as d:
   clone=Path(d)/"source";shutil.copytree(P,clone,ignore=shutil.ignore_patterns("__pycache__","gate_evidence","freshness_evidence"))
   fake=clone/"gate_worker.py"
   fake.write_text("""from pathlib import Path
import json,sys
Path(__file__).with_name("fake_executed").write_text("yes")
Path(sys.argv[3]).write_text(json.dumps({"success":True,"coupled_cases":[{"completed":True}]*18,"board_alternatives":[{},{},{}],"model_functions_replaced":False}))
""",encoding="utf-8")
   out=Path(d)/"output"
   r=subprocess.run([sys.executable,"-I","-S","-B",str(clone/"gated_run.py"),str(clone/"run_manifest.example.json"),"--output",str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,1,r.stdout+r.stderr)
   self.assertIn("gate_worker.py",r.stdout)
   self.assertFalse(out.exists());self.assertFalse((clone/"fake_executed").exists())
 def test_missing_worker_refused_before_launch(self):
  with tempfile.TemporaryDirectory() as d:
   clone=Path(d)/"source";shutil.copytree(P,clone,ignore=shutil.ignore_patterns("__pycache__","gate_evidence","freshness_evidence"))
   (clone/"gate_worker.py").unlink()
   out=Path(d)/"output"
   r=subprocess.run([sys.executable,"-I","-S","-B",str(clone/"gated_run.py"),str(clone/"run_manifest.example.json"),"--output",str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,1);self.assertFalse(out.exists())
 def test_real_worker_rejects_preexisting_results_logs_and_markers(self):
  paths=("audit-copy/results.json","audit-copy/test_log.txt","execution_trace.json","runner_started.json","worker_completion.json")
  for name in paths:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    out,context,contract,payload=self.prepare(d)
    target=out/name
    original=P/Path(name).name
    target.write_bytes(original.read_bytes() if original.exists() else b'{"old":true}')
    before=target.read_bytes()
    r=self.launch_worker(out,payload)
    self.assertNotEqual(r.returncode,0,r.stdout.decode())
    self.assertIn(b"Pre-existing output refused",r.stderr)
    self.assertEqual(target.read_bytes(),before)
    if name!="runner_started.json":self.assertFalse((out/"runner_started.json").exists())
 def test_real_worker_rechecks_snapshot_before_model_import(self):
  with tempfile.TemporaryDirectory() as d:
   out,context,contract,payload=self.prepare(d)
   source=out/"audit-copy/run_checks.py"
   source.write_bytes(source.read_bytes()+b"\n# changed after preparation\n")
   r=self.launch_worker(out,payload)
   self.assertNotEqual(r.returncode,0)
   self.assertIn(b"Execution input changed: run_checks.py",r.stderr)
   self.assertFalse((out/"runner_started.json").exists())
 def test_no_fresh_completion_means_rejection(self):
  from gated_run import fresh_output_errors
  with tempfile.TemporaryDirectory() as d:
   out,context,contract,payload=self.prepare(d)
   self.assertTrue(fresh_output_errors(out,context,contract))
   for n in ("results.json","test_log.txt"):
    shutil.copyfile(P/n,out/"audit-copy"/n)
   # Replaying archived result and old trace cannot establish this run.
   shutil.copyfile(P/"gate_evidence/execution_trace.json",out/"execution_trace.json")
   self.assertTrue(fresh_output_errors(out,context,contract))
class Notices(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  spec=importlib.util.spec_from_file_location("notices",ROOT/"tools/check_audit_notices.py")
  cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
 def test_all_13_real_entry_points(self):self.assertEqual(self.module.check(),[])
 def test_missing_comment_only_hidden_and_css_changes_refused(self):
  baseline=strict_json(P/"notice_baseline.json")
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=root/"studies/community-chain-audit";a.mkdir(parents=True)
   shutil.copyfile(P/"notice_baseline.json",a/"notice_baseline.json")
   for row in baseline:
    for e in row["files"]:
     f=root/e["path"];f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/e["path"],f)
   self.assertEqual(self.module.check(root),[])
   target=root/baseline[0]["files"][1]["path"];original=target.read_bytes()
   target.unlink();self.assertTrue(self.module.check(root))
   for value in (b"<!-- community-chain-audit -->",original.replace(b"<aside ",b"<aside hidden "),
                 original+b"<style>aside{display:none}</style>",original+b"<script>document.querySelector('aside').remove()</script>"):
    target.write_bytes(value);self.assertTrue(self.module.check(root))
   target.write_bytes(original);self.assertEqual(self.module.check(root),[])
if __name__=="__main__":unittest.main()
