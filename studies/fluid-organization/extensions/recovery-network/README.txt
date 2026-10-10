RECOVERY AND HETEROCLINIC NETWORK PILOT

Companion to the fluid-organization study, 2026-10-10.
Read report.html for completed measurements, uncertainty, controls and limits.
This package contains actual numerical simulations; it is not laboratory data.

Install Python 3.11+ and requirements.txt (requirements-lock.txt records this run).
From this directory:
  python -m pytest test_extensions.py -q
  python run_all.py

Individual steps:
  python recovery.py           # 36 three-arm fluid runs plus refinements
  python network.py            # separate three-state GLV network + learned models
  python recurrence.py         # full-field recurrence replay of 12 fluid test runs
  python make_report.py        # figures, tables, report from saved results
  python verify.py             # numerical gates and saved-data integrity

protocol.json fixes seeds, split, targets, numerical controls and thresholds.
Fluid cache entries check source and data hashes; use a new output directory
after changing simulation code or protocol. Network recordings are regenerated.
No training occurs on validation/test runs; histories use only earlier times.
Bootstrap units are independent initializations, not neighboring time samples.

The copied core.py and vendor/numerics.py are unchanged from the published
fluid pilot. numerics.py originally came from My-Sources-Project-ALL,
reports/matched-stretch/numerics.py at commit
1b12558739736d472b0eb75845cf721371fcbb71.
New recovery.py adds stage-time-dependent forcing and its work budget.

The network is an explicitly specified positive GLV three-cycle. Its offline
coefficient-identification method is not a replication of Voit and
Meyer-Ortmanns's teacher-coupled learning rule. It is not a fluid model, a
nine-saddle network, or evidence that passive fluid markers interact.

Primary source context:
Aravind & Meyer-Ortmanns (2023), On relaxation times of heteroclinic dynamics:
  https://man-aravind.github.io/assets/pdf/heteroclinic_relaxation.pdf
Voit & Meyer-Ortmanns (2019), Dynamical Inference of Simple Heteroclinic Networks:
  https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2019.00063/full
May & Leonard (1975), Nonlinear aspects of competition between three species:
  https://doi.org/10.1137/0129022

Report repository:
  https://github.com/NousVolition/Nous-Volition/tree/main/studies/fluid-organization
Code repository:
  https://github.com/NousVolition/My-Sources-Project-ALL/tree/main/reports/fluid-organization-pilot
