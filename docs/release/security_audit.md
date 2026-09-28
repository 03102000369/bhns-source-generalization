# Security and historical-path scope

The release's existing secret-pattern rules are reapplied to tracked files during final curation, with results summarized in [final_pre_push_report.md](final_pre_push_report.md). Scans cover private-key markers, common API/access tokens, credential URLs, long literal secret assignments and sensitive filenames. Findings are recorded without secret values. Pattern scanning cannot prove the absence of every possible secret.

Six frozen records intentionally retain historical workstation paths. They are inert provenance rather than executable settings, and their bytes/checksums must not be rewritten merely to remove those paths:

| Record (relative to repository root) | Historical path occurrences |
|---|---:|
| `data/manifests/rxte_acquisition_selection.csv` | 858 |
| `data/manifests/rxte_observation_inventory.csv` | 12064 |
| `data/manifests/source_aliases.csv` | 36 |
| `data/provenance/observation_provenance.csv` | 808 |
| `data/provenance/rxte_download_manifest.csv` | 4213 |
| `results/validation_heasoft/software_environment.json` | 20 |

Operational examples use relative paths or environment variables. The final curation task makes no authentication attempt or network change. An existing origin is preserved; prior authentication notes are historical and have been moved out of shared documentation.

`.local_admin/` is ignored and excluded from the release-manifest walker. It holds personal operational notes, README backups and audit receipts. Raw datasets, CALDB/HEASoft installations, article PDFs, environments and build outputs remain excluded. Only the canonical manuscript and scientific figure PDFs are distributed.
