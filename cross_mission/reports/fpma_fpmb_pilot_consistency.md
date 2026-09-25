# FPMA/FPMB pilot consistency

All four modules have response-supported 5–25 keV coverage (500 valid native channels), positive exposure, valid OGIP links and nonzero source significance in every fixed band. Independent detector rates are diagnostic count-space quantities, not physical fluxes. No spectra or responses were combined.

| ObsID | Module | Live exposure (s) | All-channel source / background counts | 5–25 net rate (count/s) | Background fraction | 18–25 significance |
|---|---|---:|---:|---:|---:|---:|
| 10601308002 | FPMA | 12183.812 | 22348 / 941 | 0.499911 ± 0.006481 | 1.602% | 10.56 |
| 10601308002 | FPMB | 12118.134 | 20409 / 874 | 0.477068 ± 0.006355 | 1.764% | 10.23 |
| 30363002002 | FPMA | 19155.151 | 490999 / 9878 | 13.767980 ± 0.026961 | 0.779% | 46.51 |
| 30363002002 | FPMB | 18706.385 | 445046 / 7841 | 12.918840 ± 0.026406 | 0.666% | 42.53 |

The FPMB/FPMA 5–25 count-rate ratios are 0.9543 and 0.9383. In individual bands the ratios range from 0.9235–1.0056 (10601308002) and 0.8518–0.9422 (30363002002). These differences are significant in the brighter pilot and require response-aware feature comparison in X2; count equality is not an acceptance criterion because module areas and response shapes differ. Neither module is empty, background-dominated over the common range, or grossly inconsistent with the same target spectrum. Source counts decrease toward high energies in both modules.

The smallest fixed-band net significance is 10.23 (LMC X-3 FPMB, 18–25 keV); this is a diagnostic, not a newly frozen cohort cut. The largest fixed-band background fraction is 10.78%. Background PSF-wing leakage is not proven absent. No claim of cross-mission calibration or common-flux accuracy follows from X1 alone.

For 30363002002 the locked bright-source trigger was applied to both modules. The post-rerun partial-bin maxima remain above 100 count/s; this is acceptable because the required screening has been applied, not because the rate was expected to decrease. See `x1_bright_screening_addendum.md`.
