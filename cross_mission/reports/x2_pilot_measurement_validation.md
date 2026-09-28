# X2 pilot measurement validation

**X2_PILOT_NEEDS_REVISION. Gate X2 remains NOT PASSED.** All four module-level A/B/C vectors were generated, but the locked continuum is not adequate for unqualified scaling. No classifier, prediction, performance metric, cohort expansion or final X3 audit was run. Scientific status remains `NOT_YET_TESTED`.

X1 passed before the first spectral fit. Input hashes link to its four accepted product sets. The measurement interface accepts only source/background/ARF/RMF paths; feature transformation accepts only four positive fluxes and their covariance. No class table or class label is accessed. Module and observation identifiers are used solely to locate and record data.

## Implemented locked design

A is log10 of observed, **model-derived energy flux** in 5–8, 8–12, 12–18 and 18–25 keV (erg cm⁻² s⁻¹). B is the four per-observation band fractions. C contains the two declared log10 hardness ratios and log10 total 5–25 keV flux. These are neither raw detector rates nor model-independent unfolded spectra. No absorption correction is applied. D remains disabled.

The same positive piecewise log-linear photon continuum is used for every spectrum. Five free log densities at 5, 8, 12, 18 and 25 keV determine the tied 3/40 keV guards. Bounds are 10⁻¹²–10³ photon cm⁻² s⁻¹ keV⁻¹; adjacent photon indices remain between −2 and 6. Integration splits native incident-energy bins at continuum knots; folding uses the actual sparse RMF and ARF. Redistribution from incident energies outside 5–25 is retained through the full response support using the tied end slopes. Guard truncation is separately tested. No response matrix was invented or modified on disk.

Source and off-source counts enter a two-Poisson likelihood with exposure/BACKSCAL scaling. The per-group background expectation is profiled analytically. Primary diagnostic grouping requires at least five background counts, preserves band edges, and applies identically to source, background and folded prediction; original PHA files remain unchanged. One- and ten-background-count alternatives assess sparse-background sensitivity. This numerical treatment follows the [official XSPEC Poisson-background statistical formulation](https://heasarc.gsfc.nasa.gov/docs/software/xspec/manual/node393.html). It is not used for RXTE model backgrounds.

Settings and investigation thresholds were recorded before fitting. The initial 96 simulations cannot resolve the predeclared p<0.01 check with a plus-one Monte Carlo p-value. A documented 399-draw precision extension retained the same continuum, bounds, features and threshold; initial results remain archived.

## Coverage and feature estimates

Every spectrum has 500 valid native channels in 5–25 keV; all four bands are supported by the response and detected. The weakest band has net significance 10.23; the largest background fraction is 10.78%. No band is extrapolated beyond reliable common response support, and no feature is missing.

| ObsID | Module | 5–8 | 8–12 | 12–18 | 18–25 |
|---|---|---:|---:|---:|---:|
| 10601308002 | FPMA | 1.7631 ± 0.0257 | 0.5165 ± 0.0135 | 0.3699 ± 0.0186 | 0.3042 ± 0.0297 |
| 10601308002 | FPMB | 1.6990 ± 0.0255 | 0.5187 ± 0.0138 | 0.3788 ± 0.0196 | 0.3079 ± 0.0294 |
| 30363002002 | FPMA | 42.5072 ± 0.0982 | 22.2949 ± 0.0722 | 9.4808 ± 0.0700 | 3.2024 ± 0.0658 |
| 30363002002 | FPMB | 41.2579 ± 0.0991 | 21.6263 ± 0.0736 | 9.1962 ± 0.0724 | 2.9595 ± 0.0655 |

Fluxes are in 10⁻¹¹ erg cm⁻² s⁻¹. Errors are local statistical 1σ from the profile-likelihood Hessian. Full covariance is retained and propagated to fractions and hardness. Conditional parametric-bootstrap scatter is also recorded. **These errors exclude continuum inadequacy, PSF-wing background mismatch and calibration systematics; they do not establish physical accuracy.**

## Fit and module diagnostics

| ObsID | Module | Deviance / nominal dof | Conditional bootstrap p | Assessment |
|---|---|---:|---:|---|
| 10601308002 | FPMA | 57.09 / 33 | 0.0100 | Borderline; requires review |
| 10601308002 | FPMB | 24.63 / 36 | 0.9350 | No fit-quality flag |
| 30363002002 | FPMA | 428.31 / 216 | 0.0025 | Poor fit; revision required |
| 30363002002 | FPMB | 288.88 / 192 | 0.0025 | Poor fit; revision required |

All optimizers converged; no parameter bound was contacted; all 399 refined bootstrap fits per module converged. Both 30363002002 modules had 0/399 simulated deviances at least as large as observed (plus-one p=0.0025; exact binomial 95% upper bound 0.00920). Coherent residual structure is visible around 5–10 keV in both modules, including a positive feature near 6–7 keV. This is evidence against treating the current smooth continuum as an adequate measurement model. It does not identify a unique physical cause. LMC X-3 FPMA is also borderline (p=0.010, 95% Monte Carlo interval 0.00155–0.0218); FPMB has p=0.935.

The residual plot `continuum_residuals.png` was visually inspected. Its standardized residuals are a diagnostic approximation; significance decisions use the joint Poisson likelihood and simulated fits.

For LMC X-3, independent module band-flux ratios FPMB/FPMA are approximately 0.964, 1.004, 1.024 and 1.012; none is a >3σ statistical discrepancy. For 30363002002 the ratios are 0.971, 0.970, 0.970 and 0.924. The first two bands differ by 8.95σ and 6.48σ statistically, while normalized shape and the two hardness coordinates have no >3σ flags. The total-flux normalization offset is about 3%, far larger than the brighter spectrum’s formal statistical error. It could include relative calibration, extraction effects or model inadequacy; statistical significance alone does not diagnose invalid calibration. No after-the-fact calibration tolerance is adopted to make these pass. The coordinate tests are correlated and are review flags, not independent hypothesis tests.

## Sensitivity and limits

Changing likelihood grouping shifts any band by at most 1.88%; truncating incident support to 3–40 keV changes any band by at most 0.54%. A uniform +3% ARF perturbation changes fitted flux by −2.91%, as expected. A small energy-dependent area tilt changes bands by at most 1.89%. These are illustrative response stresses, **not** official calibration error bars or proof that known calibration errors are covered. True alternative calibration releases and region perturbations have not been validated.

Noiseless class-independent power-law closure at photon indices 1.5, 2.5 and 4 through each actual response recovers all band fluxes to maximum relative error 2.46×10⁻⁶. This checks numerical folding/optimization for models inside the candidate family. Conditional bootstrap uncertainties and biases are reported, but these do not replace broad injection/coverage studies across curved continua, background regimes and both missions.

## Decision

The features are technically computable and reasonably stable to the tested numerical variations. The smooth continuum’s poor fit and the unresolved module normalization/calibration treatment prevent `X2_PILOT_READY_FOR_SCALE`. Stop measurement-design advancement here: document and validate a label-blind revision on these same pilots before scaling. Do not silently add source-class-specific models or choose an alternative by classification performance.

The protected common-representation design and protocol remain unchanged; no `common_representation_frozen.yaml` was created. Independent module features are diagnostics. The intended common-shape joint fit is not admitted while the underlying continuum fails; its final intensity normalization convention also remains unfrozen. See `x2_module_combination_decision_needed.md`.

Artifacts: `pilot_features.csv`, `fpma_fpmb_feature_comparison.csv`, per-module measurement JSON, `measurement_validation.json`, `pilot_settings.json`, `monte_carlo_precision_addendum.json`, and `continuum_residuals.png`, all under `results/x2_pilot/`.
