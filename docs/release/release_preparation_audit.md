# Release preparation provenance

The initial preparation audited 98,254 research-workspace files totaling 21,078,528,627 logical bytes. It selected code, frozen protocols, tabular cohorts/provenance, canonical results, tests and one manuscript package. It did not publish the workstation tree or rerun scientific experiments.

Raw RXTE/NuSTAR products, calibration/software installations, native arrays, detailed processing intermediates, downloaded literature PDFs, environments, caches and historical troubleshooting remain outside the Git payload. The original inventory found 262 files above 10 MB, 62 above 50 MB and 28 above 100 MB; none was needed as a large Git object. Full per-file inventories remain local. Aggregate exclusions are recorded in [`../workspace_exclusions.json`](../workspace_exclusions.json).

Established data/configuration/result paths are preserved. The canonical Phase-I manuscript is the reviewed LaTeX submission package; its supplement intentionally duplicates some small source/result tables. No scientific file is removed in final curation merely for its size or because it also appears in the supplement.

`main` retains Phase I and high-level Phase-II status, including a single `cross_mission/README.md` overview. `phase2-nustar` adds active code, the candidate census, acquisition manifests, product/region audits, the unchanged design lock and unfinished X2 measurement evidence. The initial seven-file Phase-II dependency addendum preserved linked region/product evidence and the extraction entry point; its exact source hashes remain in the provenance CSV.

License choice, author metadata/declarations and any future public release or DOI remain author decisions. Personal collaborator/setup notes are local-only. The [final pre-push report](final_pre_push_report.md) is the canonical record of current local curation; earlier counts and environment notes describe their own historical snapshots.
