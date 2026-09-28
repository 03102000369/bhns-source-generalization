# Module combination decision remains necessary

The locked design already intends a common-shape joint forward fit with a free relative module normalization, plus independent-module diagnostics. It explicitly leaves the reported physical-flux anchor and its systematic uncertainty to measurement validation. This pilot implements the independent diagnostics; the smooth continuum fails the bright pilot fit checks, so no combined scientific feature is admitted. No module PHA or response is co-added.

| Approach | Label-blind assessment |
|---|---|
| Separate modules | Preserves the discrepancy and is appropriate for this diagnostic. It does not define one observation-level intensity feature. |
| Statistical/exposure weighted flux | Would require the full covariance and relative/shared calibration treatment. Tiny statistical errors would dominate weights while ignoring the measured normalization offset. It is not the method intended by the locked design. |
| Common-shape joint forward fit with free normalization | Already intended by the design, but requires an adequate continuum and an explicitly fixed flux anchor/systematic convention. A numerical choice of reference module merely fixes a parameter gauge; it must not silently become the scientific intensity definition. |

The brighter pilot has nearly constant ~3% FPMA/FPMB offset in the first three bands and acceptable normalized-shape/hardness diagnostics, but both separate fits show coherent residuals. First validate a class-independent measurement-model revision; then document the intensity anchor, calibration covariance and module acceptance rule before any cohort-wide extraction of final features. No method or anchor is selected using source labels or future classification accuracy. Full X2 is NOT PASSED.
