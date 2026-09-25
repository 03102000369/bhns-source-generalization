# Scientific overview

The study tests whether detector-space X-ray spectra distinguish securely classified black-hole and neutron-star systems beyond the physical systems used for training. An observation-wise test answers whether the model recognizes another observation from an archive mixture that may already contain that binary. A source-disjoint test holds out all observations of a physical system. Identity resolution therefore precedes splitting.

The primary selected RXTE/PCA cohort contains 687 observations (122 BH and 565 NS) from 7 BH and 22 NS systems. Five source-grouped outer folds and LOSO complement the observation-wise comparison. Source-aware fitting limits the influence of prolific sources; evaluation pools observation scores into one score per source. Bootstrap intervals resample physical sources and condition on fitted predictions.

Source-label randomization assigns arbitrary labels consistently within each physical system, preserving class counts across sources. If those labels remain predictable when observations overlap between training and test, source-associated structure can support apparent classification without the real astrophysical label relation. The primary 50-permutation median AUROCs are 0.942 observation-wise and 0.461 source-grouped. The control diagnoses exploitable structure, not its unique physical or instrumental cause.

Independent HEASoft/CALDB reduction admits 207 observations of the same 29 systems. Identical-ObsID comparisons address processing choices; detector-support restrictions address specified instrumental overlap. An expanded independent cohort contains 213 observations from 9 BH and 22 NS systems. Reusing systems across checks does not create independent source replications.

Literature-based native states are kept distinct from justified common hard/soft regimes. The bounded state extension leaves only 6 BH/4 NS systems in the common hard regime and 2 BH/1 NS in the soft regime. Neither meets the five-per-class confirmatory criterion. No state-controlled classifier exists. A hardness/intensity proxy diagnostic contains class-associated information but neither establishes equivalence to full spectra nor resolves physical-state independence.

The supported conclusion is useful ranking across admitted unseen systems within RXTE/PCA, with unstable thresholds and unresolved state/instrumental dependencies. NuSTAR transfer is a separate, unfinished experiment. The canonical manuscript and frozen result tables carry the full evidence and uncertainty.
