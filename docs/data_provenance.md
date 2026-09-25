# Data provenance

Physical source and external class evidence → reviewed aliases → NASA HEASARC catalogue/archive → ObsID and acquisition selection → raw source/background/response or event products → checked reduction and rebinning → tabular features → source-disjoint folds → out-of-fold predictions → source-level summaries.

`data/reference/reference_source_roster.csv` contains the broader reference roster, including entries not admitted to the final cohort. `data/manifests/source_registry.csv`, `source_aliases.csv` and `label_provenance.csv` link class and physical identity. `rxte_acquisition_selection.csv` and `rxte_observation_inventory.csv` identify the archive candidates and predeclared selection. `data/provenance/rxte_download_manifest.csv` retains public URLs and recorded raw checksums. `data/processed/observations.csv` retains the frozen tabular reconstruction and explicit usability flags; the small independent-cohort CSVs are under `data/processed/validation_heasoft/`.

NASA's [archive overview](https://heasarc.gsfc.nasa.gov/docs/archive.html) is the authoritative access point. Original raw files and per-observation arrays/covariance/processing logs are intentionally not Git objects. Their absence is not a missing-data imputation; a full rerun must retrieve and validate actual archive bytes. An approved derived-data deposit could distribute these separately with checksums.


The standalone manuscript supplement retains its own evidence index, including hashes for the original source materials and normalized package copies. Its source paths are citations to the research workspace, not a promise that every referenced intermediate is distributed. No journal article PDF, private credential or mission calibration installation is distributed.
