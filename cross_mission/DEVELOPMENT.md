# Development setup and evidence scope

**WORK IN PROGRESS. X2 NOT PASSED. No cross-mission classifier has run.**

The current branch includes the candidate census, secure-source registry, acquisition manifests, original design lock, prospective identity-only folds, accepted X1 gate report and limited X2 diagnostic outputs. Those outputs are measurement-development evidence; they are not ML features frozen for classification. `reports/gate_status.md` is the current scientific status. `results/x2_pilot/` preserves the completed limited pilot. Do not overwrite it to make an attempted revision look like the original pilot.

## Lightweight checks

From the repository root:

```bash
python -m pytest tests cross_mission/tests -q
python scripts/verify_release.py
```

Synthetic FITS fixtures test OGIP pairing, instrument identity, grids, responses and failure behavior without downloading events. Identity-only prospective folds demonstrate source exclusion; they are explicitly not an X3 PASS or model-performance result.

## Data and reduction prerequisites

`data/reference/nustar_source_registry.csv` contains the registry; `data/manifests/nustar_inventory.csv` identifies candidates before quality screening. `download_10601308002.json` and `download_30363002002.json` contain the original pilot acquisition URLs and checksums. `src/acquire_reference.py`, `census.py` and `acquire_observation.py` document public acquisition. `src/run_pipeline.py` records both-module NuSTARDAS processing; `x1_run_tasks.py`, `x1_local_products.py` and the bright-screening helpers retain actual exposure/extraction command choices.

Install and activate HEASoft/NuSTARDAS and the official NuSTAR CALDB separately. Recorded processing versions were HEASoft 6.37.1, NuSTARDAS 2.1.6 and CALDB 20260903. The helper shell expects an active `HEADAS`, or `BHNS_CONDA_SH` plus `BHNS_HEASOFT_PREFIX` for Conda activation. Configure `PHASE2_CALDB` (or `CALDB`), `CALDBCONFIG` and `CALDBALIAS` as appropriate to your installation. `PHASE2_PFILES` must be a separate writable directory for each task. No local credentials or workstation-specific executable paths are required.

`BHNS_NUSTAR_WORK` selects physical scratch space for helpers that stage legacy-task inputs. It defaults to ignored `cross_mission/build/nustar_work/`; prefer a short, space-free external path if required by HEASoft. Its expected layout is `<ObsID>/clean/`, `<ObsID>/<A-or-B>/regions/`, and (for the bright pilot) `<ObsID>/bright_attempt001/clean/`. Restore/rebuild the clean event/attitude/mast/housekeeping files and visually approved region files before extraction. Region proposals and geometry audits are included; approval files and raw/reduced binaries are outside Git. Never fabricate a region approval. These prerequisites mean the historical reduction commands are not a turnkey clean-host pipeline.

Accepted product paths in `reports/gate_x1_report.json` are relative to `cross_mission/`. To restore the same `data/processed/nustar/` subtree on another volume, set `BHNS_NUSTAR_PRODUCTS_ROOT` to that subtree's external root. `x2_run_pilot.py` and `x2_refine_diagnostics.py` resolve those paths and verify accepted hashes. Set `BHNS_X2_OUTPUT` to a fresh attempt directory; its default is ignored `cross_mission/build/x2_pilot/`. The packaged `results/x2_pilot/` is forbidden as an output destination. Running these fit-based diagnostics is an explicit future development action, not part of release verification.

## Portability and provenance

The design protocol and design-lock hash are unchanged. Workstation prefixes in copied Phase-II reports/manifests are normalized; source versus release hashes are recorded separately. No stored numeric measurement, source census, product checksum or gate outcome is altered. Full task logs, raw events, response binaries, CALDB installations and historical filesystem troubleshooting are deliberately absent. Local paths in Phase-I frozen historical provenance remain clearly labeled exceptions; those scientific bytes were not rewritten.

Next scientific work is a label-blind X2 revision addressing continuum adequacy, module intensity normalization and systematic conventions, with new provenance. Do not scale the cohort, train classifiers or claim transfer performance before the measurement representation passes and is frozen. This remains a separate future paper.
