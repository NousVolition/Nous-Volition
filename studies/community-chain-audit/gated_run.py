"""Validate first, then execute the unchanged real runner in a separate output tree."""
from pathlib import Path
import argparse, datetime, json, os, shutil, subprocess, sys
from run_manifest import P, METADATA, integrity_errors, sha, strict_json, validate
def run(manifest_path,output,audit=P):
 audit=Path(audit).resolve();output=Path(output).resolve()
 try:
  declaration_bytes=Path(manifest_path).read_bytes()
  manifest=strict_json(manifest_path);errors=validate(manifest,audit)
 except (OSError,ValueError,TypeError) as exc:errors=[str(exc)]
 if errors:
  print("Gate refused before solver import; no run directory created.")
  print("\n".join("  - "+e for e in errors));return 1
 if output.exists() or output.is_relative_to(audit) or audit.is_relative_to(output):
  print("Output must be a new directory outside the sealed audit directory.");return 1
 pins=strict_json(audit/"manifest_sha256.json");snapshot=output/"audit-copy"
 snapshot.mkdir(parents=True)
 (output/"declaration.json").write_bytes(declaration_bytes)
 contract={k:v for k,v in manifest.items() if k not in METADATA}
 (output/"contract.json").write_text(json.dumps(contract,indent=2)+"\n",encoding="utf-8")
 for name,digest in pins.items():
  dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(audit/name,dest)
  if sha(dest)!=digest:raise RuntimeError("Snapshot hash mismatch: "+name)
 (snapshot/"manifest_sha256.json").write_bytes((audit/"manifest_sha256.json").read_bytes())
 worker=Path(__file__).with_name("gate_worker.py")
 env=os.environ.copy();env.pop("PYTHONPATH",None)
 env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONIOENCODING="utf-8",OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 command=[sys.executable,"-I","-B",str(worker),str(snapshot),str(output/"contract.json"),str(output/"execution_trace.json")]
 with (output/"runner.log").open("w",encoding="utf-8") as log:
  result=subprocess.run(command,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT)
 errors=integrity_errors(audit)
 changed=[name for name,digest in pins.items() if not (snapshot/name).is_file() or sha(snapshot/name)!=digest]
 unexpected=[name for name in changed if name not in ("results.json","test_log.txt")]
 if unexpected:errors.append("Unexpected snapshot changes: "+repr(unexpected))
 receipt=dict(started_at=start,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  profile=manifest["profile"],exit_code=result.returncode,original_pinned_files=86,
  original_pinned_files_unchanged=not integrity_errors(audit),worker_sha256=sha(worker),
  copied_runner_sha256=pins["run_checks.py"],declaration_sha256=sha(output/"declaration.json"),
  snapshot_output_changes=changed,errors=errors,scope="Real numerical fixture run; not empirical two-in-one validation")
 if result.returncode==0:
  data=strict_json(snapshot/"results.json");trace=strict_json(output/"execution_trace.json")
  receipt.update(full_coupled_runs=data["full_coupled_runs"],equation_tests=data["unit_tests"],
   observed_evolve_calls=len(trace["coupled_cases"]),board_alternatives=len(trace["board_alternatives"]),
   model_functions_replaced=trace["model_functions_replaced"],max_mass_error=data["max_mass_error"],max_divergence=data["max_divergence"])
  if not (trace["success"] and data["full_coupled_runs"]==18 and data["unit_tests"]==17 and len(trace["coupled_cases"])==18):
   errors.append("Execution accounting mismatch")
  if data["max_mass_error"]>=1e-12 or data["max_divergence"]>=1e-12:
   errors.append("Mass/divergence verification bound exceeded")
  if not all(r["grid48_72"]<r["grid24_48"] for r in data["refinement"]):
   errors.append("Grid refinement did not improve")
 (output/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(receipt,indent=2))
 return 0 if result.returncode==0 and not errors else 1
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("manifest");parser.add_argument("--output",required=True)
 args=parser.parse_args();return run(args.manifest,args.output)
if __name__=="__main__":sys.exit(main())
