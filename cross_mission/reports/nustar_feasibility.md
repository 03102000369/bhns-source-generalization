# NuSTAR source-census feasibility

Snapshot: 2026-09-23. **X0 PASS at archive-candidate level; scientific quality acceptance pending.**

The full NUMASTER snapshot contains 12,027 rows. Broad discovery covers 145 canonical source records; 111 have secure independent class evidence (18 BH, 93 NS). Public pointing/name/position criteria retain 42 systems: **11 BH and 31 NS, 251 candidate observations**. The other 34 discovery records are not promoted to secure labels. This is a broad catalogue search, not a claim of an exhaustive census of every Galactic/extragalactic binary.

The archive candidate population exceeds the predeclared ≥5 BH/≥5 NS floor. It is not yet a quality-accepted cohort. There are 22 public candidate systems beyond current Phase I (5 BH, 17 NS); none was classified from NuSTAR spectral appearance. Multiple observations do not increase the number of independent physical systems.

## Evidence and identity

Existing conservative Phase-I classifications were augmented with the dynamical sample in [BlackCAT](https://arxiv.org/abs/1510.08869), direct evidence in the [MINBAR source catalogue](https://burst.sci.monash.edu/sources), and verified primary dynamical studies: [Cyg X-1](https://arxiv.org/abs/2102.09091), [LMC X-1](https://arxiv.org/abs/0810.3447), [LMC X-3](https://arxiv.org/abs/1402.0085), and [MAXI J1820+070](https://arxiv.org/abs/1907.00938). Exact source-level references, evidence text, coordinates, and aliases are in `data/reference/nustar_source_registry.csv`. Uncertain BH mass limits and ambiguous cluster attributions remain outside automatic inclusion.

The IGR J17379-3747 / IGR J17380-3749 / XTE J1737-376 aliases resolve to one SIMBAD physical source; the retained TAP snapshot documents this merger. It is not three independent binaries. Archive-encoded signs (m/p/d) are handled only by the explicit reviewed aliases, never broad fuzzy matching. Discovery uses a 9-arcmin cone; automatic pointing identity requires both reviewed designation and ≤3-arcmin separation from independent coordinates. Larger offsets remain reviewable, not intrinsically poor observations.

## Public candidate observations per physical system

| Source | Class | Candidate observations | In current Phase I |
|---|---|---:|---|
| 4U 1543-475 | BH | 5 | True |
| Cyg X-1 | BH | 32 | False |
| GRS 1915+105 | BH | 29 | True |
| GS 1354-64 | BH | 4 | True |
| GX 339-4 | BH | 29 | True |
| LMC X-1 | BH | 4 | False |
| LMC X-3 | BH | 23 | False |
| MAXI J1820+070 | BH | 26 | False |
| V404 Cyg | BH | 9 | False |
| V4641 Sgr | BH | 2 | True |
| XTE J1859+226 | BH | 1 | True |
| 1A 1744-361 | NS | 1 | True |
| 1RXS J180408.9-342058 | NS | 3 | False |
| 4U 0614+09 | NS | 3 | True |
| 4U 1323-62 | NS | 1 | False |
| 4U 1608-522 | NS | 3 | True |
| 4U 1636-536 | NS | 5 | True |
| 4U 1705-44 | NS | 1 | True |
| 4U 1728-34 | NS | 9 | True |
| 4U 1735-444 | NS | 2 | True |
| 4U 1746-37 | NS | 1 | True |
| 4U 1812-12 | NS | 1 | False |
| Aql X-1 | NS | 3 | True |
| Cir X-1 | NS | 5 | False |
| Cyg X-2 | NS | 8 | True |
| EXO 0748-676 | NS | 3 | False |
| GRS 1741.9-2853 | NS | 1 | False |
| GX 13+1 | NS | 1 | False |
| GX 17+2 | NS | 5 | False |
| GX 3+1 | NS | 2 | False |
| IGR J00291+5934 | NS | 1 | True |
| IGR J17062-6143 | NS | 3 | False |
| IGR J17379-3747 | NS | 2 | False |
| IGR J17498-2921 | NS | 1 | False |
| IGR J17511-3057 | NS | 2 | False |
| IGR J17591-2342 | NS | 2 | False |
| MAXI J1816-195 | NS | 1 | False |
| SAX J1808.4-3658 | NS | 7 | True |
| SLX 1735-269 | NS | 1 | True |
| Ser X-1 | NS | 4 | True |
| XTE J1701-462 | NS | 2 | False |
| XTE J1739-285 | NS | 3 | False |

## Archive and processing feasibility

The [official NUMASTER catalogue](https://heasarc.gsfc.nasa.gov/W3Browse/nustar/numaster.html) supplies observation times, public availability, FPMA/FPMB exposures, target names, and issue flags. Positive catalogue exposure is not physical-file verification. Inventory rows explicitly distinguish these states. Raw and standard material for two engineering pointings was retrieved from the [official HEASARC S3 mirror](https://heasarc.gsfc.nasa.gov/docs/archive/cloud.html): LMC X-3 10601308002 and 4U 0614+09 30363002002. Each has 15 immutable level-1/auxiliary/housekeeping files, URL/timestamp/size/SHA provenance and both modules. Archive paths depend on proposal cycle; hard-coding cycle 00 returned empty listings and was corrected. Failed lookups remain recorded.

These two uncrowded engineering pointings were specified before performance analysis. They do not define the final cohort and do not authorize exclusion of bright, difficult, crowded, or poorly predicted systems. Calibration transport and module-level processing outcomes are in `nustar_processing_pilot.md`. Current archive evidence supports proceeding with measurement feasibility; the usable confirmatory source count remains unknown.

Registry: `data/reference/nustar_source_registry.csv`. Full matched/excluded inventory: `data/manifests/nustar_inventory.csv`. Summary: `results/census_summary.json`. Retrieved catalogue snapshots, sidecar hashes, and primary-source evidence are under `data/reference/evidence/`.
