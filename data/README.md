# Data access and distribution

Raw mission products are obtained through [NASA HEASARC](https://heasarc.gsfc.nasa.gov/docs/archive.html), not stored in Git. RXTE uses the XTE archive and its Standard2 products; NuSTAR uses its public observation archive. Calibration must be obtained separately from the official CALDB distribution.

Primary RXTE ObsIDs and archive identifiers are in `manifests/rxte_acquisition_selection.csv`; candidate metadata is in `manifests/rxte_observation_inventory.csv`. The frozen admitted rows are those with `usable=true` in `processed/observations.csv` (687 observations, 29 sources). Independent and expanded cohort ObsIDs are in `processed/validation_heasoft/`. Rejected observations remain explicitly recorded.

`provenance/rxte_download_manifest.csv` gives actual public URLs and recorded raw checksums. A safe release downloader can inspect these without downloading:

```bash
python scripts/download_recorded_products.py --plan
python scripts/download_recorded_products.py --output /path/to/external-storage/rxte
```

The output argument must be outside this release. Downloads are checked against recorded hashes and never overwrite an existing mismatched product. Do not turn a changed archive checksum into an automatic new scientific input.

On `phase2-nustar`, `cross_mission/data/reference/nustar_source_registry.csv`, `data/manifests/nustar_inventory.csv` and the two `download_<ObsID>.json` manifests identify NuSTAR candidates and the pilots. Its acquisition/reduction scripts retain raw bytes under ignored paths or configurable external work areas. Neither phase distributes raw event/FITS archive trees, CALDB, HEASoft, native arrays or literature PDFs. Small tabular derived features are included; larger arrays, covariance, full reduction lineage and fold-fit audits may be deposited separately only with author approval and checksums.
