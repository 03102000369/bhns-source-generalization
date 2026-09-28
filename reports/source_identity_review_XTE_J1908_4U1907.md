# XTE J1908+094 / 4U 1907+097 identity review

2026-09-22. **Objects distinct; reference-cohort assignment unresolved.**

## Evidence

[in 't Zand et al. (2002), Figure 2 and Section 2](https://arxiv.org/html/astro-ph/0205535) resolve the two X-ray objects separately. XTE J1908+094 is discussed as a black-hole candidate; this is not a dynamical mass determination. [Baykal et al.](https://arxiv.org/abs/astro-ph/0011404) study RXTE pulsar timing of 4U 1907+09, supporting a neutron star. [NASA GBM](https://gammaray.nsstc.nasa.gov/gbm/science/pulsars.html) documents the H 1907+097 alias.

[Garg et al., Section II](https://arxiv.org/html/2601.18139v1) report that ObsIDs previously assigned to XTE J1908+094 corresponded to 4U 1907+097. That is a dataset-correction claim, not an astronomical alias declaration. The inspected paper/source bundle does not provide the affected ObsID list. The unchanged Pattnaik results CSV attaches 213 observations to the former name; those 213 identifiers and measurements have not been recovered.

## Actual archive metadata

The [saved NASA query](../data/provenance/archive_query.json) selected names containing `1907` or `1908` as discovery terms only. The [returned rows](../data/provenance/archive_identity_candidates.csv) preserve names, coordinates, times, status and catalogue identifiers.

| Literal target string | Rows | Example identifier | Interpretation limit |
|---|---:|---|---|
| `4U1907+09` | 53 | `10155-01-01-00` | Archived target metadata |
| `4U1907+09_10155-01` | 2 | `10364-01-07-00` | Archive suffix retained |
| `4U_1907+09` | 159 | `10154-02-01-00` | Archived target metadata |
| `HXBG_4U1907+09` | 4 | `30267-01-51-00` | Background-style target label; do not equate automatically |
| `XTE_J1908+094` | 32 | `70408-01-01-00` | Pointing/source association needs review |
| `X1908+075` | 86 | `50079-01-01-00` | Different name/position; not a match |
| `XTE_J1908+0632` | 8 | `40434-01-01-00` | Different name/position; not a match |
| `4U 1907+097` | 1 | null | Accepted request, not an archived observation |
| `XTE J1908+094` | 4 | null | Accepted requests, not archived observations |

Total: 349 rows, 344 distinct non-null archived catalogue identifiers, five null-ID requests. [XTEMASTER documentation](https://heasarc.gsfc.nasa.gov/W3Browse/xte/xtemaster.html) states that entries may coalesce event-flag ObsIDs and that requested instrument modes can differ from actual modes. Thus catalogue syntax or a plausible total cannot verify exact data membership. The 214 rows in the first three name groups must not be coerced into the published count of 213 by dropping an arbitrary row.

The acquired probe at `70408-01-01-00` has FITS `OBJECT=XTE_J1908+094` and `DATE-OBS=2002-05-05T05:10:24`. This establishes its recorded target, not source purity, confirmed class, or membership in either ML analysis. Pointings and nearby emission require instrument-aware review before source attribution. No contamination correction was guessed.

## Conclusion, confidence and manifest actions

- High confidence: these are distinct astrophysical objects. Never map XTE J1908+094 as an alias of 4U 1907+097.
- High confidence: the independent pulsar evidence supports NS for 4U 1907+09.
- XTE J1908+094 is retained as UNRESOLVED for the trusted supervised cohort; the evidence reviewed here supports candidate status only. This is a conservative admission decision, not a claim that it is not a BH.
- Reference dataset misidentification is reported by Garg, but the exact affected rows are unresolved. The published 213 is a reported count, not 213 verified exclusions.
- No observation-level relabeling, merging, or deletion occurred. `observation_manifest.csv` and the source census remain header-only. All discovery records and the archive probe are unusable for ML. The partial literature registry contains separate IDs for the two objects, with the evidence above.

Next evidence needed: the original and corrected per-ObsID mapping plus actual file headers, coordinates/pointing and extraction logs. Only then can exact manifest edits and affected-observation counts be audited.
