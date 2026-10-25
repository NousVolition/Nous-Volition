"""Verify worker integrity and fresh outputs around the unchanged real runner.

Trust boundary: reviewed launcher code, Python environment and OS. This is not
a sandbox against a user able to rewrite the launcher or interfere with its process.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import secrets
import subprocess
import sys
from run_manifest import P, TRUSTED, METADATA, canonical, integrity_errors, sha, strict_json, strict_loads, validate

PROTOCOL = "fresh-worker-v1"
OUTPUT_NAMES = ("results.json", "test_log.txt")

def dump_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")

def regular_file(path):
    path = Path(path)
    return path.is_file() and not path.is_symlink()

def prepare_run(manifest_path, output, audit=P):
    audit, output = Path(audit).resolve(), Path(output).resolve()
    declaration_bytes = Path(manifest_path).read_bytes()
    manifest = strict_loads(declaration_bytes)  # Parse the same bytes we preserve.
    errors = validate(manifest, audit)
    if errors:
        raise ValueError("; ".join(errors))
    # Read once, compare before creating output, then execute these exact bytes
    # through stdin. A later filesystem replacement cannot change this payload.
    worker_path = audit/"gate_worker.py"
    worker_bytes = worker_path.read_bytes()
    worker_hash = hashlib.sha256(worker_bytes).hexdigest()
    if not regular_file(worker_path) or worker_hash != TRUSTED["gate_worker.py"]:
        raise ValueError("Worker integrity mismatch before launch")
    if output.exists() or output.is_symlink() or output.is_relative_to(audit) or audit.is_relative_to(output):
        raise ValueError("Output must be a new directory outside the sealed audit directory")
    pins = strict_json(audit/"manifest_sha256.json")
    # Never seed this execution with archived results.
    input_hashes = {n:h for n,h in pins.items() if n not in OUTPUT_NAMES}
    input_hashes["manifest_sha256.json"] = TRUSTED["manifest_sha256.json"]
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/"audit-copy"
    snapshot.mkdir()
    (output/"declaration.json").write_bytes(declaration_bytes)
    contract = {k:v for k,v in manifest.items() if k not in METADATA}
    dump_new(output/"contract.json", contract)
    for name, digest in input_hashes.items():
        source = audit/name
        raw = source.read_bytes()
        if not regular_file(source) or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Input changed while preparing snapshot: "+name)
        dest = snapshot/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write(raw)
    context = dict(protocol=PROTOCOL, run_nonce=secrets.token_hex(32),
                   worker_sha256=worker_hash, declaration_sha256=sha(output/"declaration.json"),
                   contract_sha256=sha(output/"contract.json"), input_hashes=input_hashes,
                   outputs_absent_before_launch=True)
    dump_new(output/"run_context.json", context)
    return context, contract, worker_bytes

def fresh_output_errors(output, context, contract):
    """Check same-run evidence, output digests and observed results; fail closed."""
    output = Path(output)
    snapshot = output/"audit-copy"
    errors = []
    try:
        required = [output/n for n in ("run_context.json","contract.json","declaration.json",
                    "runner_started.json","execution_trace.json","worker_completion.json")]
        required += [snapshot/n for n in OUTPUT_NAMES]
        missing = [str(p.relative_to(output)) for p in required if not regular_file(p)]
        if missing:
            return ["Missing or non-regular fresh output: "+n for n in missing]
        if canonical(strict_json(output/"run_context.json")) != canonical(context):
            errors.append("Run context changed")
        if sha(output/"declaration.json") != context["declaration_sha256"]:
            errors.append("Declaration changed")
        if sha(output/"contract.json") != context["contract_sha256"] or canonical(strict_json(output/"contract.json")) != canonical(contract):
            errors.append("Contract changed")
        start = strict_json(output/"runner_started.json")
        trace = strict_json(output/"execution_trace.json")
        completion = strict_json(output/"worker_completion.json")
        for name, record in (("start",start),("trace",trace),("completion",completion)):
            if record.get("protocol") != PROTOCOL or record.get("run_nonce") != context["run_nonce"]:
                errors.append("Stale or mismatched run identity: "+name)
        if start.get("real_run_checks_started") is not True or start.get("runner_sha256") != context["input_hashes"]["run_checks.py"]:
            errors.append("Real runner start missing")
        if start.get("worker_sha256") != context["worker_sha256"] or completion.get("worker_sha256") != context["worker_sha256"]:
            errors.append("Wrong worker in completion evidence")
        if completion.get("success") is not True or trace.get("success") is not True or trace.get("runner_returned") is not True:
            errors.append("Real runner did not complete")
        if trace.get("model_functions_replaced") is not False:
            errors.append("Solver replacement reported")
        for name in ("declaration_sha256","contract_sha256"):
            if completion.get(name) != context[name]:
                errors.append("Completion does not match current "+name)
        if completion.get("trace_sha256") != sha(output/"execution_trace.json") or completion.get("start_sha256") != sha(output/"runner_started.json"):
            errors.append("Completion evidence digest mismatch")
        hashes = {name:sha(snapshot/name) for name in OUTPUT_NAMES}
        if completion.get("output_sha256") != hashes:
            errors.append("Results changed after worker completion")
        writes = trace.get("observed_output_writes",[])
        if len(writes) != 2 or sorted(w["path"] for w in writes) != sorted(OUTPUT_NAMES):
            errors.append("Both fresh output writes were not observed")
        elif any(w.get("completed") is not True or w["sha256"] != hashes[w["path"]] or type(w.get("characters")) is not int or w["characters"] <= 0 for w in writes):
            errors.append("Output-write witness mismatch")
        for name,digest in context["input_hashes"].items():
            if not regular_file(snapshot/name) or sha(snapshot/name) != digest:
                errors.append("Execution input changed: "+name)
        observed = trace.get("coupled_cases",[])
        if len(observed) != len(contract["cases"]):
            errors.append("Wrong number of observed coupled cases")
        else:
            for got, expected in zip(observed,contract["cases"]):
                for key in ("case_id","parameters","intervals","max_dt"):
                    if canonical(got.get(key)) != canonical(expected[key]):
                        errors.append("Observed case does not match declaration: "+expected["case_id"]+"/"+key)
                if got.get("completed") is not True or got.get("A_start") != expected["initial"]["A"]:
                    errors.append("Case incomplete or initial history changed")
                err = got.get("initial_field_max_error")
                if type(err) not in (int,float) or not math.isfinite(err) or not 0<=err<=1e-12:
                    errors.append("Invalid initial-field check")
                if len(got.get("rows",[])) != len(expected["intervals"]):
                    errors.append("Missing observed output intervals")
        if canonical(trace.get("board_alternatives")) != canonical(contract["board_alternatives"]):
            errors.append("Board alternative checks incomplete")
        data = strict_json(snapshot/"results.json")
        if type(data.get("unit_tests")) is not int or data["unit_tests"] != 17 or type(data.get("full_coupled_runs")) is not int or data["full_coupled_runs"] != 18:
            errors.append("Result count mismatch")
        # The archived runner saves 12 primary cases; the trace also contains
        # the three role-swap and three offset runs.
        saved = data.get("results",[])
        primary = [r for r in observed if r["case_id"].split("/")[1].startswith("n")]
        if len(saved) != 12 or len(primary) != 12:
            errors.append("Primary result coverage mismatch")
        else:
            for row,witness in zip(saved,primary):
                law,label = witness["case_id"].split("/")
                if row["law"] != law or row["configuration"] != label or row["n"] != witness["parameters"]["n"] or canonical(row["rows"]) != canonical(witness["rows"]):
                    errors.append("Saved result differs from observed return")
        log = (snapshot/"test_log.txt").read_text(encoding="utf-8")
        if not re.search(r"^Ran 17 tests in ",log,re.M) or not re.search(r"^OK\s*$",log,re.M) or len(re.findall(r"^test_.* \.\.\. ok$",log,re.M)) != 17:
            errors.append("Fresh equation-test log does not show 17 successful tests")
        for key in ("max_mass_error","max_divergence"):
            value=data.get(key)
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<1e-12:
                errors.append("Numerical verification bound failed: "+key)
        refinement=data.get("refinement",[])
        if len(refinement)!=3 or not all(0<=r["grid48_72"]<r["grid24_48"] for r in refinement):
            errors.append("Grid refinement failed")
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError) as exc:
        errors.append("Malformed/incomplete fresh evidence: "+str(exc))
    return errors

def run(manifest_path, output, audit=P):
    audit, output = Path(audit).resolve(), Path(output).resolve()
    try:
        context, contract, worker_bytes = prepare_run(manifest_path, output, audit)
    except (OSError,ValueError,TypeError) as exc:
        print("Gate refused before worker launch: "+str(exc))
        return 1
    env=os.environ.copy()
    env.pop("PYTHONPATH",None)
    env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONIOENCODING="utf-8",OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    # '-' reads the already verified worker payload from stdin, not from a
    # mutable script path. No model function or output is mocked.
    command=[sys.executable,"-I","-B","-",str(output/"audit-copy"),str(output/"run_context.json")]
    with (output/"runner.log").open("wb") as log:
        result=subprocess.run(command,input=worker_bytes,cwd=output/"audit-copy",env=env,stdout=log,stderr=subprocess.STDOUT)
    errors=integrity_errors(audit)
    if result.returncode != 0:
        errors.append("Worker exited unsuccessfully: "+str(result.returncode))
    errors += fresh_output_errors(output,context,contract)
    receipt=dict(protocol=PROTOCOL,run_nonce=context["run_nonce"],success=not errors,
                 started_at=start,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 profile=contract["profile"],exit_code=result.returncode,
                 original_pinned_files=86,original_pinned_files_unchanged=not integrity_errors(audit),
                 worker_sha256=context["worker_sha256"],worker_verified_before_launch=True,
                 verified_worker_bytes_executed_via_stdin=True,
                 archived_outputs_copied=False,outputs_absent_before_launch=True,
                 fresh_output_verification=not errors,
                 copied_runner_sha256=context["input_hashes"]["run_checks.py"],
                 declaration_sha256=context["declaration_sha256"],
                 errors=errors,scope="Real numerical fixture run; not empirical two-in-one validation")
    if not errors:
        data=strict_json(output/"audit-copy/results.json")
        trace=strict_json(output/"execution_trace.json")
        receipt.update(full_coupled_runs=data["full_coupled_runs"],equation_tests=data["unit_tests"],
                       observed_evolve_calls=len(trace["coupled_cases"]),board_alternatives=len(trace["board_alternatives"]),
                       model_functions_replaced=trace["model_functions_replaced"],max_mass_error=data["max_mass_error"],
                       max_divergence=data["max_divergence"],output_sha256=strict_json(output/"worker_completion.json")["output_sha256"])
    dump_new(output/"receipt.json",receipt)
    print(json.dumps(receipt,indent=2))
    return 0 if not errors else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    return run(args.manifest,args.output)

if __name__=="__main__":
    sys.exit(main())
