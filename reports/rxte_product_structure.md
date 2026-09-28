# Actual PCA product structures

The first inspection sampled 78 observations across both classes before bulk reconstruction. The final programmatic inspection covers every successfully reconstructed observation; failures remain in excluded_observations.csv.

Source/background: PRIMARY, SPECTRUM and STDGTI; OGIP type-I Standard2, 129 native channels, COUNTS, EXPOSURE, explicit STAT_ERR, AREASCAL and BACKSCAL. Responses contain EBOUNDS and SPECRESP MATRIX; HDU order varies, so extensions are selected by name. Detector membership is read from ROWIDn. Filter files contain XTE_MKF and sampled detector-on states. Some telemetry diagnostic values are missing; these are retained as null with finite-data fractions, never invented as zero.

Source SAEXTRCT counts are integer sums over selected anodes/PCUs; the spectral exposure equals the summed GTI **wall-clock** duration, not PCU-seconds. Standard light curves instead contain explicit fcalc RATE/ERROR scaling in HISTORY and use top-layer selections. They therefore must not be compared directly with all-layer spectral rates. The broad guide’s normalization statement cannot be blindly applied to every PHA. This pipeline divides verified summed spectral rates by the number of selected PCUs, requiring all selected PCUs to remain on in sampled GTIs. Products needing separate exposure/detector treatment are rejected for later re-extraction.

The archived source/background GTIs can differ by one floating-point ULP (about 6e-8 s); matching permits at most 1e-6 s with zero relative tolerance. Statistical errors are read from STAT_ERR in the native count units, divided by exposure and area scaling, then propagated through background subtraction and rebinning. Only explicitly declared POISSERR counts may use square-root counts. No zero-filled substitutes are allowed. These formal errors do not quantify uncertain background-model or response calibration.

| role | source | class_label | obsid | date | native_channels | pcus | net_rate |
|---|---|---|---|---|---|---|---|
| earliest | GX 339-4 | BH | 10420-01-01-00 | 1996-07-26T18:20:32 | 48 | [0, 1, 2, 3, 4] | 115.3545 |
| latest | GX 339-4 | BH | 96409-01-14-00 | 2011-04-05T06:57:20 | 46 | [2] | 0.8545 |
| brightest | XTE J1550-564 | BH | 30191-01-02-00 | 1998-09-19T23:59:28 | 48 | [0, 1, 2, 3, 4] | 6343.001 |
| faintest | XTE J1118+480 | BH | 92427-01-01-00 | 2007-01-12T14:59:28 | 46 | [2, 4] | -0.0542 |
| earliest | 4U 1608-522 | NS | 10093-01-01-01 | 1996-03-15T19:28:16 | 56 | [0, 1, 2, 3, 4] | 37.0839 |
| latest | 4U 0614+09 | NS | 96307-01-10-00 | 2011-12-29T21:48:48 | 46 | [2] | 121.7041 |
| brightest | Cyg X-2 | NS | 70014-02-02-00 | 2002-12-31T15:39:28 | 45 | [2, 3] | 887.6557 |
| faintest | SAX J1808.4-3658 | NS | 95407-01-01-00 | 2010-01-20T07:47:44 | 46 | [2] | -0.5284 |

Representative rows may fail the final count-rate cut; this inspection deliberately covers faint products too. Exact HDUs, PCUs, count rates, error definitions, filter diagnostics, native-grid identifiers and response histories are retained in product_inspection.json and individual processing records.
