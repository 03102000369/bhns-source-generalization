# Instrument-screening addendum


## Bright-screening completion addendum

The 30363002002 one-second corrected lightcurves triggered the locked >100 count/s rule in one FRACEXP=0.024994 bin per module (156.07/164.26 count/s). Full-bin maxima were 88.29/91.13 count/s. The trigger was not waived after inspection. Both modules were rerun from verified original level-1 inputs in `x1_bright_attempt001`, retaining optimized SAA/tentacle screening and using `(STATUS==b0000xxx00xxxx000)&&(SHIELD==0)`. The added shield veto follows the [current official spectroscopy FAQ](https://heasarc.gsfc.nasa.gov/docs/nustar/nustar_faq.html); the protected design document was not edited. All task exits were zero.

The good-time intervals, bad-pixel tables, exposure, attitude, and mast arrays are unchanged. Randomized subpixel detector/aperture-stop coordinates differ by up to about 1.09 SKY pixels; new official exposure maps were therefore generated. All source/background aperture pixels have nonzero exposure. The new source-center offsets are 1.63/1.46 arcsec, within the fixed 60 arcsec apertures. The updated images `30363002002_A_bright.png` and `30363002002_B_bright.png` were visually reviewed: compact isolated target, no additional source or distinct stray-light/ghost-ray arc in the apertures. Extended target PSF wings remain a background systematic to quantify; absence of any PSF flux is not asserted. Regions are PASS for both final modules.

Final evidence: `results/x1_pilot/bright_geometry.json`, `data/processed/nustar/30363002002/x1_bright_attempt001/{command.json,nupipeline.log,staged_inputs.json}`, and each module's `exposure_bright` and `products_bright` directories.
