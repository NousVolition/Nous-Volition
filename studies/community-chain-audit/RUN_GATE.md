# Run gate: enforced declarations and the unchanged real runner

Repaired 24 October 2026. This version closes the gaps found in the supplied patch. It supports one explicitly reviewed profile, `sealed-audit-run-checks-v2`. It is a numerical verification gate; acceptance does not certify empirical corpus validation.

## What is enforced

1. Before importing a solver, the gate checks the full declaration against `run_contract.json`, its trusted hash, the immutable audit manifest, and all 86 audit-file hashes. Missing or altered additions, inheritance, cases, initial fields, inputs, alternatives, selected laws or coefficients are refused. Unknown profiles are refused. Metadata cannot change the computation.
2. The complete contract contains 18 ordered coupled cases, three separate board alternatives, all 20 numerical/assembly/verification groups N01–N20, the exact 17-test verification program, and a file/line inventory of its numerical literals. The signed S+10 initial condition is explicit. Grid restrictions are even integers at least 12; 2D is an implementation choice. S has no corpus positivity requirement.
3. Inheritance is explicitly reviewed in `inheritance_review.json`. The only inherited code for this profile is the pinned legacy PDE implementation from `community_two_in_one_field`, classified as a numerical fixture. The old encounters study is not silently made a dependency. Other source-chain entries retain explicit bounded descriptions; absence of a keyword never implies corpus provenance.
4. An accepted declaration runs the original `run_checks.py`, byte-for-byte, in a new output directory. A Python profiling observer records real calls and checks parameters, initial field shapes, inputs, history and alternatives. It does not replace or mock any solver function. Initial-field comparison tolerance 1e-12 is an added verification rule.
5. The archive remains unchanged. Only the disposable execution copy may replace its own `results.json` and `test_log.txt`. All other copied files and all 86 originals are checked after execution. A receipt, observed execution trace, logs and fresh results are preserved separately.
6. CI validates before model execution, invokes only the gated route for this audit job, then rechecks the sealed archive and notices. Its run artifacts are uploaded.
7. The notice check requires all 26 explicitly listed README/report files for 13 studies. It checks the substantive notice and reviewed whole-file render envelope. Deletion, a hidden comment, CSS hiding, or script changes fail. Whole-file hashes are intentionally conservative: a legitimate report edit needs an explicit notice-baseline review.

The trust anchor is this reviewed gate code and its Git commit. Someone able to edit that code and replace its hashes can define a new policy. This does not sandbox a hostile repository owner or prevent direct manual invocation of the archived runner. It enforces this CLI and CI execution path. Other studies and new parameter sweeps require their own reviewed profiles; they are not silently admitted as equivalent.

## Corpus rows implemented

The patch itself adds no field equation. The unchanged solver implements these register rows:

| Data row | Source | Relation | Scope |
|---|---|---|---|
| 5 | P229–230 | Momentum | Coupled momentum and incompressibility |
| 6 | P261–264 | Responses | Three distinct laws exercised separately |
| 7 | P263–264 | Gradient alternatives | Three coded; main coupled cases use raw; alternatives have identity tests |
| 9 | P517–532 | Transport/history | Signed-field transport and explicit accumulator prehistory |
| 10 | P545–557 | Stress | Diagnostic; not an independent momentum feedback |

Sens/Sin, architecture, consistency, boundary utility and reciprocal transform are not newly implemented by this runner. Smoke/Clay labels remain metadata in these fixtures. No measured personal history or empirical full two-in-one validation is supplied.

## Every substantive rule added by this gate

These are engineering controls, not extra corpus laws:

- One fixed supported profile, exact case ordering and type-sensitive complete-contract comparison; descriptive metadata is limited to study, run ID, valid ISO date and author.
- Strict JSON: duplicate keys and nonfinite constants are refused.
- Source and policy SHA256 checks before execution. A changed source requires a new reviewed contract, even if a regex would still recognize the old labels.
- A complete parameter allowlist and checks of the corpus coefficient domains, with explicit implementation restrictions for grid and vector dimension. The sealed case values restrict this fixture, not all possible corpus solutions.
- Empirical validation claims are always false for this numerical fixture. Removing additions cannot turn it into a validation result.
- Explicit dependency records, distinguishing code reuse from inherited validity. No keyword-based status inference.
- New, separate output directory; byte-preserved copies; isolated Python child process; fixed single-thread environment; no output overwrite or source-directory output.
- Read-only profiling of actual model calls; initial-state maximum error at most 1e-12; expected case and alternative counts; conservation/divergence below 1e-12; decreasing grid discrepancies. These are verification criteria, not new dynamics.
- Only results and test-log files may change in the execution copy; the original 86 must remain identical. Receipts report actual execution and failures.
- Explicit 13-study/26-file notice inventory, exact substantive notice text, visible-text parsing and conservative whole-file hash review.
- CI admission before execution, after-run integrity checks and saved run artifacts.

N01–N20 in the contract list all substantive inherited numerical choices. See also the earlier [equation and additions inventory](../community-connection-resolution/REGISTER_AND_ADDED_RULES.md). The exact source-pinned verification program and literal inventory make the auxiliary test constants inspectable; they do not turn those constants into corpus requirements.

## Reproduce

From `studies/community-chain-audit`, using Python 3.12:

```text
python -m pip install -r requirements.txt
python verify.py
python run_manifest.py run_manifest.example.json
python -m unittest test_run_manifest.py -v
python gated_run.py run_manifest.example.json --output /absolute/new/output-directory
python verify.py
python ../../tools/check_audit_notices.py
```

Use a new output directory each time. On Windows clone with `git -c core.autocrlf=false -c core.longpaths=true clone https://github.com/NousVolition/Nous-Volition.git` to preserve the repository's mixed original line endings and long filenames. Do not normalize the 86 pinned files.

## Evidence and remaining work

The [real-run receipt](gate_evidence/receipt.json), [execution trace](gate_evidence/execution_trace.json), [fresh results](gate_evidence/results.json), [equation-test log](gate_evidence/test_log.txt) and [gate-test log](gate_evidence/gate_tests.log) record the repaired run. It executes the actual 18 coupled cases, all three separate board checks and 17 equation tests. The admission and notice regression suite uses real files and the real gate CLI, without mocks.

The remaining empirical work is unchanged: observation functions for Smoke, Clay, moving idea forms, intended meaning and each person's history have not been identified and independently validated by these numerical fixtures. These enforcement repairs do not close that scientific question.
