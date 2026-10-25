"""Regression checks use the real gate CLI and real files; no mocks."""
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
    r=subprocess.run([sys.executable,"-B",str(P/"gated_run.py"),str(f),"--output",str(out)],capture_output=True,text=True)
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
    r=subprocess.run([sys.executable,"-B",str(clone/"gated_run.py"),str(clone/"run_manifest.example.json"),"--output",str(out)],capture_output=True,text=True)
    self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertIn("run_checks.py",r.stdout);self.assertFalse(out.exists())
 def test_changed_contract_or_trust_manifest_refused(self):
  with tempfile.TemporaryDirectory() as d:
   clone=Path(d)/"source";shutil.copytree(P,clone,ignore=shutil.ignore_patterns("__pycache__","gate_evidence"))
   for name in TRUSTED:
    p=clone/name;before=p.read_bytes();p.write_bytes(before+b" ")
    self.assertTrue(integrity_errors(clone));p.write_bytes(before)
 def test_existing_output_and_audit_output_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(run(P/"run_manifest.example.json",Path(d)),1)
  self.assertEqual(run(P/"run_manifest.example.json",P/"new-output"),1);self.assertFalse((P/"new-output").exists())
 def test_original_86_still_unchanged(self):self.assertEqual(integrity_errors(),[])
 def test_ci_uses_gate_before_real_runner(self):
  workflow=(ROOT/".github/workflows/blank.yml").read_text(encoding="utf-8")
  job=workflow[workflow.index("  corpus-chain-audit-checks:"):]
  self.assertNotIn("python run_checks.py",job)
  self.assertNotIn("python -m unittest test_audit.py",job)
  self.assertLess(job.index("python run_manifest.py"),job.index("python gated_run.py"))
  self.assertIn("python studies/community-chain-audit/verify.py",job)
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
