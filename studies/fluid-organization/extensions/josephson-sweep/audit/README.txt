INITIAL DIRECT-PHASE NUMERICAL CHECKS: FAILED, NOT FINAL RESULTS

The first implementation integrated phi1 and phi2 directly in double precision.
Its energy budget passed but time-step and independent-solver voltage gates
failed. Near the critical current, phase separations can become much smaller
than machine spacing and later regrow. Subtracting two rounded phases loses
this state information and can artificially synchronize a pair.

The final model preserves p=(phi1+phi2)/2 and z=log|tan((phi1-phi2)/4)|.
Its exact equations are p'=(i+sin(p)*tanh(z))/(1+2alpha), z'=-cos(p).
See the report and diagnose_precision.py for a small reproducible demonstration.
The initial gates were not relaxed. Initial sources, protocol and failed-check
summaries are archived here. The bulky superseded direct-phase trace files
are excluded from the published package; final accepted traces are in data/.

To reproduce the initial full pilot in a separate directory, copy the five
initial_*.py / initial_protocol.json source files here while removing the
initial_ prefix. Run run_sweep.py, validate.py, analyze.py in that directory.
The initial analyze.py is expected to fail its numerical acceptance gates.
It must not be used to replace the accepted final results.
