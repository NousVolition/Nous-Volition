"""Execute the byte-identical runner and attest freshly observed output writes.

This worker is hash-checked by the parent and executed from those checked bytes.
Its completion record is meaningful only within that trusted launcher boundary.
"""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import os
import runpy
import sys

OUTPUT_NAMES = ("results.json", "test_log.txt")
PROTOCOL = "fresh-worker-v1"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")

def main():
    audit = Path(sys.argv[1]).resolve()
    context_path = Path(sys.argv[2]).resolve()
    output = audit.parent
    if context_path != output / "run_context.json":
        raise RuntimeError("Unexpected context location")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if context["protocol"] != PROTOCOL:
        raise RuntimeError("Unknown freshness protocol")
    nonce = context["run_nonce"]
    if len(nonce) != 64 or any(c not in "0123456789abcdef" for c in nonce):
        raise RuntimeError("Invalid run nonce")
    # Check all inputs and absence of old outputs before importing the model.
    for name, digest in context["input_hashes"].items():
        path = audit / name
        if not path.resolve().is_relative_to(audit) or path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise RuntimeError("Execution input changed: " + name)
    for path in [audit / n for n in OUTPUT_NAMES] + [output / n for n in (
        "execution_trace.json", "runner_started.json", "worker_completion.json")]:
        if path.exists() or path.is_symlink():
            raise RuntimeError("Pre-existing output refused: " + path.name)
    if sha(output / "contract.json") != context["contract_sha256"]:
        raise RuntimeError("Contract bytes changed")
    if sha(output / "declaration.json") != context["declaration_sha256"]:
        raise RuntimeError("Declaration bytes changed")
    contract = json.loads((output / "contract.json").read_text(encoding="utf-8"))
    import numpy as np
    expected = contract["cases"]
    trace = dict(protocol=PROTOCOL, run_nonce=nonce, coupled_cases=[], board_alternatives=[],
                 observed_output_writes=[], model_functions_replaced=False,
                 runner_returned=False)
    sys.path.insert(0, str(audit))
    runner = str(audit / "run_checks.py")
    field = str(audit / "audited_field.py")
    active = {}
    writes = {}
    started = False

    def profile(frame, event, arg):
        nonlocal started
        filename = frame.f_code.co_filename
        caller = frame.f_back
        if filename == runner and frame.f_code.co_name == "run":
            if event == "call":
                if started:
                    raise RuntimeError("Unexpected second runner invocation")
                started = True
                dump_new(output / "runner_started.json", dict(
                    protocol=PROTOCOL, run_nonce=nonce, real_run_checks_started=True,
                    runner_sha256=context["input_hashes"]["run_checks.py"],
                    worker_sha256=context["worker_sha256"]))
            elif event == "return":
                trace["runner_returned"] = True
        if filename == field and frame.f_code.co_name == "evolve" and caller and caller.f_code.co_filename == runner:
            if event == "call":
                i = len(trace["coupled_cases"])
                if i >= len(expected):
                    raise RuntimeError("Undeclared coupled case")
                e = expected[i]
                v = frame.f_locals
                params = asdict(v["p"])
                params["direction"] = list(params["direction"])
                if params != e["parameters"]:
                    raise RuntimeError("Observed solver parameter drift")
                for key in ("person", "intervals", "max_dt", "initial_state_basis"):
                    if v[key] != e[key]:
                        raise RuntimeError("Observed case drift: " + key)
                init = e["initial"]
                if v["A"] != init["A"] or v["start"] != init["start"]:
                    raise RuntimeError("History drift")
                z = v["z"]
                n = params["n"]
                if z.shape != (3, n, n):
                    raise RuntimeError("Initial field shape drift")
                x, y = np.meshgrid(2*np.pi*np.arange(n)/n, 2*np.pi*np.arange(n)/n, indexing="ij")
                wanted = np.array([
                    init["speed"]*np.sin(x)*np.cos(y),
                    -init["speed"]*np.cos(x)*np.sin(y),
                    np.full_like(x, init["total"]+init["offset"])+init["texture"]*np.cos(x)*np.cos(y)])
                physical = np.fft.ifft2(z, axes=(-2, -1))
                error = float(abs(physical-wanted).max())
                if error > 1e-12:
                    raise RuntimeError("Initial field differs from declared shape")
                row = dict(case_id=e["case_id"], parameters=params, initial_field_max_error=error,
                           A_start=v["A"], initial_mean_S=float(physical[2].real.mean()),
                           max_dt=v["max_dt"], intervals=v["intervals"], completed=False)
                trace["coupled_cases"].append(row)
                active[id(frame)] = row
            elif event == "return":
                row = active.pop(id(frame))
                if arg is None:
                    raise RuntimeError("Evolution did not return")
                row.update(completed=True, A_end=float(arg[1]), rows=arg[2])
        if filename == runner and frame.f_code.co_name == "alternative" and event == "call":
            v = frame.f_locals
            i = len(trace["board_alternatives"])
            if i >= len(contract["board_alternatives"]):
                raise RuntimeError("Undeclared alternative")
            e = contract["board_alternatives"][i]
            actual = dict(lam=v["lam"], mu=v["mu"], inputs=[list(x) for x in v["inputs"]])
            if actual != {k:e[k] for k in actual}:
                raise RuntimeError("Alternative equation fixture drift")
            trace["board_alternatives"].append(dict(name=e["name"], **actual))
        # Observe actual Path.write_text calls made by the pinned runner. Do not
        # replace write_text, the runner, the solver, or the test result object.
        if frame.f_code.co_name == "write_text" and caller and caller.f_code.co_filename == runner:
            if event == "call":
                target = Path(frame.f_locals["self"]).resolve()
                if target.parent != audit or target.name not in OUTPUT_NAMES:
                    raise RuntimeError("Unexpected runner output")
                if target.exists() or target.is_symlink():
                    raise RuntimeError("Refusing to overwrite prior runner output")
                data = frame.f_locals["data"]
                encoding = frame.f_locals.get("encoding")
                if encoding != "utf-8":
                    raise RuntimeError("Unexpected runner output encoding")
                raw = data.replace("\n", os.linesep).encode("utf-8")
                writes[id(frame)] = (target, len(data), hashlib.sha256(raw).hexdigest())
            elif event == "return":
                target, length, digest = writes.pop(id(frame))
                if arg != length or not target.is_file() or sha(target) != digest:
                    raise RuntimeError("Output write did not complete as observed")
                trace["observed_output_writes"].append(dict(
                    path=target.name, characters=length, sha256=digest, completed=True))

    try:
        sys.setprofile(profile)
        runpy.run_path(runner, run_name="__main__")
        sys.setprofile(None)
        if not started or not trace["runner_returned"]:
            raise RuntimeError("Runner did not complete")
        if len(trace["coupled_cases"]) != 18 or not all(r["completed"] for r in trace["coupled_cases"]):
            raise RuntimeError("Missing completed coupled cases")
        if len(trace["board_alternatives"]) != 3:
            raise RuntimeError("Missing alternative checks")
        if sorted(w["path"] for w in trace["observed_output_writes"]) != sorted(OUTPUT_NAMES):
            raise RuntimeError("Fresh output writes not observed")
        for name, digest in context["input_hashes"].items():
            if sha(audit / name) != digest:
                raise RuntimeError("Execution input changed during run: " + name)
        trace["success"] = True
        dump_new(output / "execution_trace.json", trace)
        output_hashes = {name:sha(audit/name) for name in OUTPUT_NAMES}
        if output_hashes != {w["path"]:w["sha256"] for w in trace["observed_output_writes"]}:
            raise RuntimeError("Outputs changed after observed write")
        dump_new(output / "worker_completion.json", dict(
            protocol=PROTOCOL, run_nonce=nonce, success=True,
            worker_sha256=context["worker_sha256"],
            declaration_sha256=context["declaration_sha256"],
            contract_sha256=context["contract_sha256"],
            trace_sha256=sha(output/"execution_trace.json"),
            start_sha256=sha(output/"runner_started.json"),
            output_sha256=output_hashes))
    except BaseException as exc:
        sys.setprofile(None)
        trace.update(success=False, error=repr(exc))
        if not (output/"execution_trace.json").exists():
            dump_new(output/"execution_trace.json", trace)
        raise

if __name__ == "__main__":
    main()

