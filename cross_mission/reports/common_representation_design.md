# Common representation: predeclared measurement design

Status: **CANDIDATE_DESIGN_NOT_VALIDATED**. The locked protocol records the definitions below before any Phase-II classification. There are no fitted physical features yet.

## What is comparable

Use observed energy flux in four fixed bands: **5–8, 8–12, 12–18, and 18–25 keV**. A common class-independent incident continuum is forward-folded through each observation's native response and fitted to its own source/background data. Integrate the fitted observed continuum in these bands. Units are erg cm⁻² s⁻¹. These are **model-dependent observed-flux estimates**, neither detector count space nor model-independent unfolded spectra. No absorption correction is applied. Matching detector-channel edges alone is insufficient.

The candidate continuum is positive and piecewise log-linear in photon density on nodes 3, 5, 8, 12, 18, 25, and 40 keV. Outer nodes are guard nodes constrained by adjacent-slope extrapolation, not additional scientific features. The draft bounds are 10⁻¹²–10³ photons cm⁻² s⁻¹ keV⁻¹, with adjacent photon indices −2 to 6. These broad bounds and the continuum family require numerical validation; recording them does not certify their stability. The fitted channel range remains 5–25 keV. Redistribution from outside that range must be handled and tested with the guard nodes. A future change requires a documented measurement-design revision before ML, never selection by target AUROC.

Use the same continuum and band integrals for every BH, NS, and mission. NuSTAR FPMA/FPMB are jointly fitted with a common shape and a free module normalization; independently fitted module fluxes provide an agreement diagnostic. Module spectra and responses are not co-added. Define and freeze which module normalization anchors the reported flux and its systematic uncertainty during validation.

## Predeclared representations

| Family | Coordinates | Role |
|---|---|---|
| A | log10 of the four observed band fluxes | Primary; retains amplitude |
| B | Four band fluxes divided by their summed 5–25 keV flux | Shape-only comparison; fixed per-observation normalization |
| C | log10(F8–12/F5–8), log10(F18–25/F12–18), log10(F5–25) | Coarse hardness/intensity comparison |
| D | Optional shared phenomenological parameters | Secondary, disabled pending separate validation |

The implemented transformations in `src/contracts.py` accept already measured positive physical fluxes. They do not extract a flux from a count spectrum. Tests of scale invariance or numerical finiteness certify these transformations only, not astrophysical measurement accuracy.

## Correct statistical treatment

NuSTAR extracted source/background spectra require an appropriate Poisson source-plus-background likelihood with exposure/area scaling. The RXTE background is modeled, not an independent Poisson off-source measurement. Inspection of the protected RXTE PHA products finds `POISSERR=False` and explicit `STAT_ERR` in both source and background. Their propagated error semantics must be preserved and validated, including any systematic/calibration treatment. Applying W-stat indiscriminately to both instruments would be wrong. Identical physical feature definitions do not require an incorrect identical noise likelihood. See the official [XSPEC statistics documentation](https://heasarc.gsfc.nasa.gov/docs/software/xspec/manual/node393.html) and [flux model documentation](https://heasarc.gsfc.nasa.gov/docs/software/xspec/manual/XSmodelCflux.html).

## Required measurement validation

1. Recover known class-independent continua through actual RXTE and NuSTAR responses, spanning slope, curvature, flux, background, and exposure. Quantify band bias, uncertainty coverage, and guard-node sensitivity.
2. Demonstrate convergence and inspect fit residuals, parameter-bound contacts, missingness, and flux uncertainties on a multi-source label-blind pilot. Record every failure rather than dropping difficult fits silently.
3. Compare FPMA/FPMB fluxes and shapes with uncertainty; test response/calibration perturbations and extraction-region sensitivity. Check all four bands have usable response coverage.
4. Define measurement-quality thresholds using these diagnostics, without BH/NS prediction errors. Do not transfer RXTE's >5 count s⁻¹ rule to NuSTAR.
5. Freeze accepted sources, observation identities, products, fit code, bounds, uncertainty method, quality rules, module normalization convention, and all hashes in `configs/common_representation_frozen.yaml` only after passing validation.

NuSTAR features may be inspected for this prespecified instrument/measurement audit. They may not fit a classifier's scaler, feature-selection model, tuning process, threshold, or calibration in zero-shot evaluation. A/B/C are compared as declared; the primary family cannot be changed based on their classification scores.

## Subsequent experiment

After X2, serialize final physical-source folds and validate X3. Tune simple prior/logistic-regression/random-forest models only within the training mission using source-disjoint inner validation. All RXTE observations of an outer NuSTAR test system are excluded. Use equal total training weight per source, training-only preprocessing, fixed threshold 0.5, mean clipped observation log-odds per physical source, and source-bootstrap uncertainty. The locked protocol specifies grids, seeds, and controls. Zero-shot results precede any separately declared adaptation.
