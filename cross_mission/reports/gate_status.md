# Phase-II gate status — X1 completion and limited X2 pilot

Scientific verdict: **NOT_YET_TESTED**. Classification authorization: **false**. Earliest unsatisfied gate: **X2**. No scientific classifier, prediction, performance metric, final leakage audit, or cohort expansion was executed.

| Gate | Status | Evidence / remaining condition |
|---|---|---|
| X0 — secure source census | PASS | Existing protected census and archive candidates unchanged; this is not the quality-accepted cohort |
| X1 — NuSTAR reduction | PASS | Both existing pilots, FPMA and FPMB: 4/4 region-validated source/background/ARF/RMF sets, real task logs, OGIP checks and hashes |
| X2 — common representation | NOT PASSED — pilot validation only | A/B/C generated for four modules; X2_PILOT_NEEDS_REVISION because the locked continuum has poor fit diagnostics and normalization/systematic conventions are not frozen |
| X3 — scientific leakage audit | NOT RUN | Prospective folds unchanged; final accepted-cohort audit still requires X2 |
| X4 — within-mission models | NOT RUN | X2–X3 prerequisites unmet |
| X5 — RXTE → NuSTAR zero-shot | NOT RUN | No scientific model, prediction or performance evaluation |
| X6 — reverse transfer | NOT RUN | Quality-accepted source diversity remains unestablished |
| X7 — confounder controls | NOT RUN | No mission/source/random-label classifier or adaptation |

X1 evidence: `gate_x1_report.md`, `gate_x1_report.json`, `results/x1_pilot/product_pairing_audit.csv` and `results/x1_pilot/response_audit.csv`. The eight official missing depth-cut RMFs are recovered; all four regions pass visual and detector/exposure review. The bright-screening trigger on 30363002002 was honored by rerunning level 1 for both modules.

X2 evidence: `x2_pilot_measurement_validation.md`, `x2_module_combination_decision_needed.md`, and `results/x2_pilot/`. Both bright-pilot module fits fail the predeclared conditional Poisson fit-quality diagnostic. Numerical closure and finite features do not establish an adequate physical measurement. Independent features are diagnostic only; no measurement freeze exists.

The census, prospective folds and locked design are included. Phase I remains frozen. Historical task logs and intermediate read/recovery records remain in the original workspace; release validation is summarized in `docs/validation_record.md`.

## Exactly one next action

**Document and validate a label-blind X2 measurement-design revision on these two pilots, resolving continuum inadequacy and the module intensity normalization/systematic convention before any cohort scaling.**

Phase I remains frozen. Intended publication route: **SEPARATE_PHASE2_PAPER**.
