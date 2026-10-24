# Effective time-step correction

The frozen plan requests a half-step check on grid 48. The first execution used max_dt=.004 and .002, but the diffusion stability cap reduced both to the same effective dt=0.1/79. Those two rows are duplicate configurations, not time-refinement evidence.

After inspecting the output, add two runs with max_dt equal to half the actual grid-48 step, namely 0.1/158. Preserve the initial duplicate rows and label them. This corrects the verification procedure; it changes no equation, observation mapping, parameter-search range, selected witness or outcome threshold. Report 75 completed runs, comprising 73 distinct configurations, rather than counting the duplicate rows as independent evidence.
