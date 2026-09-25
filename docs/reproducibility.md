# Reproducibility

## A. Lightweight verification and rendering

Install with `python -m pip install -r requirements.txt` in a virtual environment, from the release root. Run:

```bash
python -m pytest -q
python scripts/verify_release.py
python scripts/reproduce_tables.py
python scripts/render_journal_figures.py
bash manuscript/build.sh
```

The verifier checks the detached manifest chain, every packaged payload hash, exact tracked-file coverage once Git is initialized, primary cohort counts, frozen result identities and the state gate. Unit tests cover aliases, source separation, train-only preprocessing, source weights, randomization and result serialization. One historical full-workspace integrity test is explicitly marked `full_workspace`; it requires thousands of omitted arrays/records and is excluded by default. Two archive-dependent state suites tied to old manuscript drafts were not copied; release tests verify the final state conclusion directly.

`reproduce_tables.py` reconstructs the main performance table from frozen CSVs and writes input hashes. The six-figure renderer preserves original plotting logic, removes the obsolete whole-workspace verifier dependency, and writes only `build/reproduced/figures/`. It verifies packaged inputs before and after rendering. Scientific numbers are unchanged; PDF/SVG timestamps, fonts and renderer versions can prevent byte-identical plots. The archived publication PDFs remain fixed and separately verified.

TeX compilation requires pdfLaTeX, BibTeX and the packages listed in `manuscript/README.md`. The main/supplement sources and official MNRAS class/style are unchanged. The build script works in an ignored output copy, preserving tracked sources and PDFs.

## B. Full raw-data regeneration

This release supplies code and acquisition/cohort manifests, not a turnkey clean-host raw-reduction proof. Use a **separate disposable clone/work directory**, never the immutable tagged checkout, for legacy writers. They write data/results and several have safeguards tied to omitted historical full-workspace manifests.

For the primary archive route, `scripts/build_rxte_inventory.py`, `acquire_rxte_products.py` and `reconstruct_rxte_cohort.py` document discovery, acquisition and reconstruction. Prefer `scripts/download_recorded_products.py --plan` for a safe list of the retained public raw URLs; actual download requires an explicit external output directory and verifies recorded SHA-256 values. Archive availability or revised bytes may require review, not forced checksum replacement.

Independent validation uses `scripts/acquire_validation_raw.py`, `reduce_validation_heasoft.py`, `audit_heasoft_products.py`, `assemble_heasoft_validation.py` and the frozen HEASoft protocol. Install HEASoft/CALDB separately; set `BHNS_HEASOFT_PREFIX` and `CALDB` as documented by `scripts/validation_heasoft_env.sh`. No installation/reduction runs in CI. Historical reducers can depend on omitted manifests, full per-observation lineage and local environment details; restore those from an author-approved derived-data archive or reconstruct them under an explicitly reviewed new run record. Changed processing/code hashes must not be presented as the original frozen run.

The original audited workspace contains roughly 21.1 GB of logical files, including intermediate duplication and its environment. This is not an estimate of fresh-run peak storage. Allow substantial external storage, archive transfer time and processing time. Full regeneration has not been executed in this release task. No models were scientifically retrained.

## Integrity scope

`RELEASE_MANIFEST.csv` covers every distributable payload file. Its own hash is in `RELEASE_MANIFEST.sha256`; that checksum file cannot meaningfully hash itself. `.git/`, ignored build/cache files and `.release_audit/` / `.local_admin/` local preparation records are outside this manifest. The exhaustive workstation inventory and large-file CSV remain local and ignored; aggregate exclusions and precise included-file provenance are distributed. After intentional changes, maintainers must review and regenerate the manifest with `scripts/update_release_manifest.py`; never use regeneration to conceal an unexpected integrity failure.

The [release audit](release/phase1_release_audit.md) records Phase-I preservation; the [final pre-push report](release/final_pre_push_report.md) records local curation checks. Personal GitHub setup and collaborator notes are deliberately local-only.
