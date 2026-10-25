"""Adversarial checks against a freshly completed real gated run.

CI invokes gated_run.py first, then passes its new directory here. This program
does not generate simulated successes or replace the runner/model. Faults are
injected only into disposable copies of the actual completed execution.
"""
import sys
if __name__ == "__main__":
    if not (sys.flags.isolated and sys.flags.no_site) or sys.flags.optimize:
        raise SystemExit("Use non-optimized python -I -S test_fresh_outputs.py --run-dir NEW_RUN")
    sys.dont_write_bytecode = True
    from pathlib import Path
    import types
    for name in ("run_manifest","gated_run"):
        path=Path(__file__).resolve().with_name(name+".py")
        module=types.ModuleType(name)
        module.__file__=str(path)
        sys.modules[name]=module
        exec(compile(path.read_bytes(),str(path),"exec"),module.__dict__)
from pathlib import Path
import argparse
import json
import shutil
import tempfile
from gated_run import dump_new, fresh_output_errors, prepare_run
from run_manifest import P, TRUSTED, integrity_errors, sha, strict_json

def check(run_dir):
    run_dir = Path(run_dir).resolve()
    context = strict_json(run_dir/"run_context.json")
    contract = strict_json(run_dir/"contract.json")
    receipt = strict_json(run_dir/"receipt.json")
    assert not integrity_errors(), "Source integrity failed"
    assert context["worker_sha256"] == TRUSTED["gate_worker.py"]
    assert receipt["success"] is True and receipt["fresh_output_verification"] is True
    assert receipt["run_nonce"] == context["run_nonce"]
    assert not fresh_output_errors(run_dir, context, contract), "Real run did not pass"
    checks = []

    def edit(path, change):
        data = strict_json(path)
        change(data)
        path.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    def bind_trace(copy):
        edit(copy/"worker_completion.json",
             lambda d: d.update(trace_sha256=sha(copy/"execution_trace.json")))
    def reject(name, copy, expected, ctx=context, con=contract):
        errors = fresh_output_errors(copy, ctx, con)
        assert errors and any(expected in e for e in errors), (name, errors)
        checks.append(dict(name=name, rejected=True, errors=errors))

    with tempfile.TemporaryDirectory(prefix="fresh-output-regressions-") as tmp:
        base = Path(tmp).resolve()
        def duplicate(name):
            target = base/name
            assert target.resolve().is_relative_to(base)
            shutil.copytree(run_dir, target)
            return target

        # Replay a fully valid completed run into a different prepared run.
        replay = base/"replay"
        new_context, new_contract, _ = prepare_run(P/"run_manifest.example.json", replay)
        assert new_context["run_nonce"] != context["run_nonce"]
        for name in ("runner_started.json","execution_trace.json","worker_completion.json"):
            shutil.copyfile(run_dir/name, replay/name)
        for name in ("results.json","test_log.txt"):
            shutil.copyfile(run_dir/"audit-copy"/name, replay/"audit-copy"/name)
        reject("valid_old_run_replayed_as_new", replay, "run identity", new_context, new_contract)

        for i, name in enumerate(("audit-copy/results.json", "audit-copy/test_log.txt",
                                  "worker_completion.json", "runner_started.json", "execution_trace.json")):
            copy = duplicate("missing-"+str(i))
            (copy/name).unlink()
            reject("missing_"+name, copy, "Missing or non-regular")
        for i, name in enumerate(("results.json", "test_log.txt")):
            copy = duplicate("changed-output-"+str(i))
            with (copy/"audit-copy"/name).open("ab") as stream:
                stream.write(b"\nchanged after completion\n")
            reject("changed_"+name, copy, "Results changed after worker completion")

        for name, change, expected in (
            ("missing_write_witness", lambda d:d.update(observed_output_writes=[]),
             "Both fresh output writes were not observed"),
            ("runner_not_returned", lambda d:d.update(runner_returned=False),
             "Real runner did not complete"),
            ("case_incomplete", lambda d:d["coupled_cases"][0].update(completed=False),
             "Case incomplete"),
            ("case_parameter_changed", lambda d:d["coupled_cases"][0]["parameters"].update(nu=0.4),
             "Observed case does not match declaration"),
        ):
            copy = duplicate(name)
            edit(copy/"execution_trace.json", change)
            bind_trace(copy)  # Also test semantic checks, beyond a digest mismatch.
            reject(name, copy, expected)

        copy = duplicate("saved-return-mismatch")
        edit(copy/"audit-copy/results.json", lambda d:d["results"][0].update(n=999))
        changed_hash = sha(copy/"audit-copy/results.json")
        def alter_witness(data):
            for write in data["observed_output_writes"]:
                if write["path"] == "results.json":
                    write["sha256"] = changed_hash
        edit(copy/"execution_trace.json", alter_witness)
        edit(copy/"worker_completion.json",
             lambda d:d["output_sha256"].update({"results.json":changed_hash}))
        bind_trace(copy)
        reject("saved_result_disagrees_with_observed_return", copy, "Saved result differs")

        copy = duplicate("input-changed")
        with (copy/"audit-copy/run_checks.py").open("ab") as stream:
            stream.write(b"\n# changed after run\n")
        reject("execution_input_changed_after_completion", copy, "Execution input changed")

    assert not fresh_output_errors(run_dir, context, contract), "Regression changed original evidence"
    assert not integrity_errors(), "Regression changed source"
    result = dict(success=True, real_run_nonce=context["run_nonce"],
                  real_runner_executed=True, solver_functions_mocked=False,
                  rejected_scenarios=len(checks), checks=checks,
                  original_86_unchanged=True, original_completed_run_unchanged=True)
    dump_new(run_dir/"fresh_output_regressions.json", result)
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    raise SystemExit(check(args.run_dir))

