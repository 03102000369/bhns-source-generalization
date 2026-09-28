# Pilot extraction-region validation

Scope: two existing pilot observations, both modules, before any class-model analysis. Region decisions use coordinates, event morphology, detector identities, and official exposure maps. No class label or prediction enters the region algorithm.

The retained policy uses 60-arcsec source circles centered on the measured per-module centroid and 90-arcsec background circles 180 arcsec away. Independent catalogue positions are RA/Dec 84.73596816896/−64.08425498264 for 10601308002 and 94.28062/9.137067 for 30363002002. Centroid offsets are 3.1–4.7 arcsec, within the locked 30-arcsec identity-review rule. Source and background geometric areas are 11,309.734 and 25,446.900 square arcsec respectively; their separation exceeds the sum of radii by approximately 30 arcsec, so there is no overlap.

The [official nuexpomap task](https://heasarc.gsfc.nasa.gov/docs/software/lheasoft/help/nuexpomap.html) incorporates bad/hot pixels, detector gaps, attitude, and mast motion. Non-vignetted maps were generated with the installed documented parameters, `pixbin=5`, and `initseed=yes`. They measure geometric exposure; spectral effective-area/vignetting corrections are subsequently computed by the standard extraction workflow. Per-module commands, logs, exposure maps, DET1 maps, and aspect histograms are preserved in `data/processed/nustar/OBSID/x1_{A,B}/exposure/`.

| Observation | Module | Source minimum / 5th-percentile live-exposure fraction | Background minimum / 5th percentile | Zero-exposure aperture pixels | Region verdict |
|---|---|---|---|---|---|
| 10601308002 | FPMA | 0.998 / 1.000 | 0.694 / 0.899 | 0 in both | PASS |
| 10601308002 | FPMB | 0.928 / 0.981 | 0.877 / 0.960 | 0 in both | PASS |
| 30363002002 | FPMA | 0.998 / 1.000 | 0.839 / 0.983 | 0 in both | PASS |
| 30363002002 | FPMB | 0.722 / 0.929 | 0.875 / 0.987 | 0 in both | PASS |

These measurements explicitly show partial exposure: the apertures are not claimed to remain entirely on fully live pixels at every instant. All selected pixels have usable exposure. The standard exposure/PSF corrections and observation-specific BACKSCAL account for partial coverage. This is a reviewed geometry decision, not an invented universal count-rate or quality threshold. X1 still requires valid extracted products and responses.

For 10601308002, the northern background remains on source detector 0 and avoids the detector transitions approached by the eastern candidate. For 30363002002, the southern background avoids the western field edge and northern/eastern detector transitions. Per-module centroid differences are retained instead of forcing identical coordinates. Radii remain as predeclared.

Visual inspection finds no distinct nearby contaminating point source, stray-light arc, or ghost-ray structure in the selected apertures. Source PSF wings do not end abruptly at the aperture boundary; residual wing/background sensitivity remains a measurement systematic and is assessed using extracted band background fractions. No claim of zero PSF-wing contamination is made. The source optical-response corrections remain enabled in nuproducts.

`data/manifests/nustar_pilot_regions.csv` contains exact coordinates, areas, region paths, coverage statistics, author, timestamp, decision, and exception reason. Each new region directory contains an `approval.json` with evidence paths and file hashes. The prior provisional manifest/regions remain unchanged. The visual audit is separate in `nustar_pilot_region_visual_audit.md`.


## Bright-screening completion addendum

The 30363002002 one-second corrected lightcurves triggered the locked >100 count/s rule in one FRACEXP=0.024994 bin per module (156.07/164.26 count/s). Full-bin maxima were 88.29/91.13 count/s. The trigger was not waived after inspection. Both modules were rerun from verified original level-1 inputs in `x1_bright_attempt001`, retaining optimized SAA/tentacle screening and using `(STATUS==b0000xxx00xxxx000)&&(SHIELD==0)`. The added shield veto follows the [current official spectroscopy FAQ](https://heasarc.gsfc.nasa.gov/docs/nustar/nustar_faq.html); the protected design document was not edited. All task exits were zero.

The good-time intervals, bad-pixel tables, exposure, attitude, and mast arrays are unchanged. Randomized subpixel detector/aperture-stop coordinates differ by up to about 1.09 SKY pixels; new official exposure maps were therefore generated. All source/background aperture pixels have nonzero exposure. The new source-center offsets are 1.63/1.46 arcsec, within the fixed 60 arcsec apertures. The updated images `30363002002_A_bright.png` and `30363002002_B_bright.png` were visually reviewed: compact isolated target, no additional source or distinct stray-light/ghost-ray arc in the apertures. Extended target PSF wings remain a background systematic to quantify; absence of any PSF flux is not asserted. Regions are PASS for both final modules.

Final evidence: `results/x1_pilot/bright_geometry.json`, `data/processed/nustar/30363002002/x1_bright_attempt001/{command.json,nupipeline.log,staged_inputs.json}`, and each module's `exposure_bright` and `products_bright` directories.
