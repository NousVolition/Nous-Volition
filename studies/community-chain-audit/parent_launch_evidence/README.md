# Isolated parent-launch evidence

Recorded 24 October 2026, America/Los_Angeles; UTC timestamps fall on 25 October. This run uses the repaired parent and worker startup path, Python 3.12, and the unchanged audit requirements. The numerical runner and solver functions were not mocked.

- `prior_bypass_findings.json` preserves the earlier private-copy attack: an added local `subprocess.py` reused old results and obtained false success without changing the gate source or 86 pinned files.
- `parent_launch_tests.log` records 10 passing tests. They exercise that exact launch attack, module/package/bytecode shadows, checker source substitution, unchecked checker caches, unsafe flags, working-directory and environment injection, startup hooks, and imported execution.
- `gate_tests.log` records all 31 existing gate/notice tests passing.
- `receipt.json`, `run_context.json`, `runner_started.json`, `execution_trace.json`, and `worker_completion.json` record the actual run and its digest bindings. The receipt includes parent startup flags, the standard-library `subprocess` origin and the numerical dependency directories.
- `results.json`, `test_log.txt`, and `runner.log` are copied byte-for-byte from the completed real run: 18 coupled cases, 3 board alternatives and 17 equation tests.
- `fresh_output_regressions.json` records 14 rejected replay, missing-evidence and tampering scenarios using copies of that actual completed run.
- The original verification, declaration and notice logs establish unchanged hashes for all 86 originals and intact notices at all 13 audited entry points.
- `source_hashes.json` identifies the exact supplemental sources tested; `evidence_sha256.json` preserves this evidence's byte hashes.

The two generated audit outputs are flattened into this directory for publication; the 84 copied inputs are not duplicated. Their output hashes match the completion record.

Use the required `python -I -S` commands in [RUN_GATE.md](../RUN_GATE.md). The reviewed launcher, interpreter, installed numerical dependencies and operating system remain trust assumptions. These unsigned records are not independent authentication of an untrusted bundle and do not establish empirical validation of the two-in-one model. Earlier evidence directories remain historical records.
