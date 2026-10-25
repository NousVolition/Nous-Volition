# Run gate: enforced declarations and the unchanged real runner

Updated 24 October 2026. The worker/freshness repair still allowed the parent to import an untracked local `subprocess.py`. A reproduced attack intercepted the launch, reused old results and rebound their identifiers and hashes without changing the gate source or any of the 86 pinned files. This revision requires isolated parent startup, verifies and explicitly loads the checker source, and tests that exact attack before rerunning the real solver. It supports one explicitly reviewed profile, `sealed-audit-run-checks-v2`. It is a numerical verification gate; acceptance does not certify empirical corpus validation.

## What is enforced

1. The CLI must start with `python -I -S gated_run.py`. Before any path-based import, the built-in `sys` module is used to require isolated startup, no automatic site loading, safe paths and no optimization. The repository and current directory are not added to the import path. The checker is read once, compared with the launcher's expected SHA256, and compiled from those bytes, so a package or cached bytecode cannot substitute it. The gate then checks the full declaration, reviewed contract, immutable manifest and all 86 audit hashes. Local standard-library module/package collisions in the audit directory or working directory are refused. An imported `run()` cannot claim a gated execution.
2. The complete contract contains 18 ordered coupled cases, three separate board alternatives, all 20 numerical/assembly/verification groups N01–N20, the exact 17-test verification program, and a file/line inventory of its numerical literals. The signed S+10 initial condition is explicit. Grid restrictions are even integers at least 12; 2D is an implementation choice. S has no corpus positivity requirement.
3. Inheritance is explicitly reviewed in `inheritance_review.json`. The only inherited code for this profile is the pinned legacy PDE implementation from `community_two_in_one_field`, classified as a numerical fixture. The old encounters study is not silently made a dependency. Other source-chain entries retain explicit bounded descriptions; absence of a keyword never implies corpus provenance.
4. An accepted declaration runs the original `run_checks.py`, byte-for-byte, in a new output directory. A Python profiling observer records real calls and checks parameters, initial field shapes, inputs, history and alternatives. It does not replace or mock any solver function. Initial-field comparison tolerance 1e-12 is an added verification rule.
5. Before launch the parent compares the worker with an expected SHA256 in the reviewed gate policy, reads its bytes once, and executes those checked bytes through `python -I -S -B -`. Replacing the worker pathname afterward cannot substitute the payload. Missing or altered workers fail before an output directory is created. The worker appends only the selected interpreter environment's installed numerical package directories after the standard library; it does not run site customization or `.pth` hooks. The receipt records startup flags, the parent's actual `subprocess` module path and those dependency directories.
6. The archive remains unchanged. The execution copy contains the 84 archived input files plus the original manifest, but neither archived output. The worker rechecks input hashes and refuses existing result, test-log, start, trace or completion files before importing the model. Each launch has a random 256-bit identifier. The observer sees the real runner start, return and write both outputs; the completion record binds their hashes to that identifier, declaration, contract and trace. The parent checks these bindings and matches saved results to observed solver returns. All copied inputs and all 86 originals are checked afterward.
7. CI runs the 31 existing gate/notice tests and 10 parent-launch tests, invokes the isolated gated route, then runs 14 replay, missing-output and tampering checks on disposable copies of that completed real run. It rechecks the sealed archive and notices and uploads the run artifacts.
8. The notice check requires all 26 explicitly listed README/report files for 13 studies. It checks the substantive notice and reviewed whole-file render envelope. Deletion, a hidden comment, CSS hiding, or script changes fail. Whole-file hashes are intentionally conservative: a legitimate report edit needs an explicit notice-baseline review.

The trust anchor is this reviewed gate code and its Git commit, running with a trusted Python environment and operating system. Someone able to edit the launcher and its expected hashes, replace runtime dependencies, or interfere with its process remains outside this protection. This does not prevent direct manual invocation of the archived runner. A JSON receipt is not a signed certificate and is not independently authentic if supplied by an untrusted party. These controls enforce the reviewed CLI and CI execution path. Other studies and new parameter sweeps require their own reviewed profiles; they are not silently admitted as equivalent.

Use the required startup flags from the beginning. A Python process started without isolation can run its configured startup hooks before any script gets control; the gate cannot retroactively sanitize such a process. Its old plain-Python invocation now refuses rather than attempting an unsafe automatic relaunch. The dedicated startup-hook test includes a positive control proving the injected hook executes without `-S` and remains inactive under the supported invocation.

Freshness means the current invocation actually produced and checked the output. A deterministic rerun may produce identical numerical bytes. Timestamps or differences from old numbers are not used as proof of freshness; absence before launch, observed writes and the current run identifier establish it within the trusted execution boundary.

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
- Source, policy and worker SHA256 checks before execution. The worker payload is executed from the checked bytes. A changed source requires explicit review, even if a regex would still recognize the old labels.
- Required isolated, no-site, non-optimized startup; checker SHA256 and direct source compilation; refusal of standard-library shadows; no execution through an imported `run()`. Worker package paths are taken from the selected installed interpreter environment without processing startup hooks. These are launch controls, not field equations.
- A complete parameter allowlist and checks of the corpus coefficient domains, with explicit implementation restrictions for grid and vector dimension. The sealed case values restrict this fixture, not all possible corpus solutions.
- Empirical validation claims are always false for this numerical fixture. Removing additions cannot turn it into a validation result.
- Explicit dependency records, distinguishing code reuse from inherited validity. No keyword-based status inference.
- New, separate output directory; byte-preserved input copies with archived outputs excluded; isolated Python child process; fixed single-thread environment; no output overwrite or source-directory output.
- Read-only profiling of actual model calls; initial-state maximum error at most 1e-12; expected case and alternative counts; conservation/divergence below 1e-12; decreasing grid discrepancies. These are verification criteria, not new dynamics.
- Results and test-log files must be created during this invocation; other execution inputs and the original 86 must remain identical. The worker refuses old markers and writes start/trace/completion files exclusively. Receipts report actual execution and failures.
- A random 256-bit run identifier binds start, trace and completion records. Output-write observation, content hashes, exact case accounting, return-value comparisons and successful 17-test log checks are required. These are engineering verification rules, not additions to the field equations.
- Explicit 13-study/26-file notice inventory, exact substantive notice text, visible-text parsing and conservative whole-file hash review.
- CI admission before execution, after-run integrity checks and saved run artifacts.

N01–N20 in the contract list all substantive inherited numerical choices. See also the earlier [equation and additions inventory](../community-connection-resolution/REGISTER_AND_ADDED_RULES.md). The exact source-pinned verification program and literal inventory make the auxiliary test constants inspectable; they do not turn those constants into corpus requirements.

## Reproduce

From `studies/community-chain-audit`, using Python 3.12:

```text
python -m pip install -r requirements.txt
python verify.py
python -I -S run_manifest.py run_manifest.example.json
python -I -S test_run_manifest.py -v
python -I -S test_parent_launch.py -v
python -I -S gated_run.py run_manifest.example.json --output /absolute/new/output-directory
python -I -S test_fresh_outputs.py --run-dir /absolute/new/output-directory
python verify.py
python ../../tools/check_audit_notices.py
```

Use a new output directory each time. On Windows clone with `git -c core.autocrlf=false -c core.longpaths=true clone https://github.com/NousVolition/Nous-Volition.git` to preserve the repository's mixed original line endings and long filenames. Do not normalize the 86 pinned files.

## Evidence and remaining work

The new [real-run receipt](parent_launch_evidence/receipt.json), [execution trace](parent_launch_evidence/execution_trace.json), [completion record](parent_launch_evidence/worker_completion.json), [results](parent_launch_evidence/results.json), [equation-test log](parent_launch_evidence/test_log.txt), [31-test gate log](parent_launch_evidence/gate_tests.log), [10-test parent-launch log](parent_launch_evidence/parent_launch_tests.log) and [14 replay/tampering checks](parent_launch_evidence/fresh_output_regressions.json) record this revision. The actual runner executes 18 coupled cases, three separate board checks and 17 equation tests. No solver or runner function is replaced. Deliberately fake modules and workers appear only as negative test inputs and are rejected before execution.

The 31 gate tests include altered/missing workers, archived output injection, stale marker injection and input changes before model import. The 14 checks use copies of the newly completed real run, including replay of its fully valid evidence into a new run with a different identifier. They also remove evidence, corrupt outputs, change case parameters and create disagreements between saved results and observed returns. Checks that deliberately rebind hashes exercise the substantive comparisons as well as digest checks.

The parent-launch tests cover the exact fake-`subprocess.py` and old-result attack; local module/package/sourceless-bytecode shadows; working-directory injection; `PYTHONPATH` and startup environment injection; a fake checker package and unchecked bytecode cache; altered checker source; `.pth` and site customization hooks; unsafe startup flags and imported execution. The original attack's [private-copy findings](parent_launch_evidence/prior_bypass_findings.json) are retained with the new evidence.

The earlier `gate_evidence/` and `freshness_evidence/` directories remain historical records. Their real numerical executions were genuine, but neither established adequate protection of the parent's launch path.

The remaining empirical work is unchanged: observation functions for Smoke, Clay, moving idea forms, intended meaning and each person's history have not been identified and independently validated by these numerical fixtures. These enforcement repairs do not close that scientific question.
