# Black-Hole and Neutron-Star Classification Beyond Known Sources

This project tests whether X-ray spectra distinguish black-hole and neutron-star binaries when the test systems are absent from training. Repeated observations of the same binary can share source and instrumental structure, so physical source identity must be resolved before splitting the data.

## Phase I — RXTE/PCA

**Scientifically complete and frozen.** The primary cohort contains 687 observations from 29 systems: 7 BH and 22 NS. The study compares observation-wise and source-disjoint evaluation, leave-one-source-out (LOSO) evaluation, source-label randomization, independent HEASoft validation and detector-support controls.

Useful ranking survives source holdout in this selected cohort. The small BH census, instrument dependence, uncertain score calibration and unstable classification thresholds limit its interpretation. Physical-state independence remains unestablished: the confirmatory state comparison was not run because the common hard regime contains only 6 BH and 4 NS systems, below the five-per-class criterion. See [methods](docs/methodology.md) and [limitations](docs/limitations.md).

## Phase II — RXTE → NuSTAR

**WORK IN PROGRESS.** A separate future study asks whether an RXTE-trained classifier generalizes to unseen physical systems observed with NuSTAR.

- X0 PASS
- X1 PASS
- X2 NOT PASSED
- X3–X7 NOT RUN
- Cross-mission classification NOT YET TESTED

See [current status](docs/phase2_status.md). Active code and pilot evidence are on `phase2-nustar`; `main` contains Phase I and a brief Phase-II overview.

## Repository structure

| Path | Contents |
|---|---|
| `src/`, `scripts/`, `configs/` | Methods, reproduction tools and frozen protocols |
| `data/` | Source identity, ObsIDs, provenance and tabular cohorts |
| `results/` | Frozen metrics and predictions |
| `manuscript/` | Canonical manuscript, figures and self-contained supplement |
| `tests/` | Software and scientific-integrity checks |
| `docs/` | Methods, interpretation, reproduction and release provenance |
| `cross_mission/` | Overview on main; active NuSTAR materials on `phase2-nustar` |

## Reproduction

From the repository root, with Python 3.11+:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/verify_release.py
python scripts/reproduce_tables.py
python scripts/render_journal_figures.py
bash manuscript/build.sh
```

On `phase2-nustar`, run `python -m pytest tests cross_mission/tests -q` for the combined suite. Table and figure rebuilding uses frozen results without retraining; output goes to `build/`. Manuscript compilation also requires TeX. Full raw-data regeneration needs HEASoft/CALDB, archive downloads and substantial storage/time; a clean-host end-to-end rerun has not been demonstrated. See [reproducibility](docs/reproducibility.md).

## Data

Raw mission data come from [NASA HEASARC](https://heasarc.gsfc.nasa.gov/docs/archive.html) and are not stored in Git. [Data access](data/README.md) describes the included ObsID lists, public URLs and checksums. Calibration trees and downloaded literature PDFs are excluded.

## Manuscript

The [Phase-I manuscript and supplement](manuscript/README.md) retain their scientific content. The immutable snapshot is tagged `v1.0.0-phase1-paper`. Author metadata and declarations still need approval; Phase II remains a separate paper.

## Citation

`CITATION.cff` is structurally valid but has an explicit author TODO and is not yet a publication-ready citation. Authorship, citation metadata and licensing remain [author decisions](manuscript/AUTHOR_TODOS.md). No DOI or project license is claimed.
