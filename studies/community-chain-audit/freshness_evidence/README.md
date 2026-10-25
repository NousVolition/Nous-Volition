# Worker integrity and fresh-output evidence

Recorded 24 October 2026 (the run timestamps are UTC, 25 October). The run used Python 3.12 on Windows with the audit requirements installed. It executed the unchanged original runner through the repaired gate. No solver function was mocked.

- `receipt.json`: accepted real run, 18 coupled cases, 17 equation tests, 3 board alternatives, all 86 original hashes unchanged.
- `run_context.json`, `runner_started.json`, `execution_trace.json`, `worker_completion.json`: current-run identifier, observed execution, output-write records and digest bindings.
- `results.json`, `test_log.txt`, `runner.log`: newly produced outputs, copied byte-for-byte from the disposable execution directory.
- `fresh_output_regressions.json`: 14 adversarial scenarios rejected using disposable copies of the actual completed run. The original accepted run remained unchanged.
- `gate_tests.log`: all 31 admission, integrity and notice tests passed, including fake-worker and old-output injection tests.
- `original_verify.log`, `declaration_check.log`, `notice_check.log`: 86-file verification, accepted declaration and all 13 notice entry points.
- `source_hashes.json`: exact supplemental source and policy versions used for these checks.
- `evidence_sha256.json`: byte hashes of this saved evidence.

The run directory contained an `audit-copy/` subdirectory; this publication stores its two generated outputs directly here to avoid duplicating all 84 archived input files. Their hashes still match the completion record. Reproduce with the commands in [RUN_GATE.md](../RUN_GATE.md); use a new output directory.

These records document the reviewed execution. They are not signed certificates, protection against a rewritten gate/runtime, or empirical validation of the two-in-one model. The previous `gate_evidence/` record remains available: its successful numerical execution did not establish adequate worker/freshness enforcement.
