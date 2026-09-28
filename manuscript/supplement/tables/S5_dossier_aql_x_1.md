# Aql X-1: targeted NS evidence review

Source class: independently verified NS in the frozen cohort; native taxonomy is study-specific. Processed targets: 8. This review does not classify all archival observations of the source.

## Manuscripts and review scope

- [zhang1998](https://arxiv.org/abs/astro-ph/9711282) — retained_review_rechecked
- [cui1998](https://arxiv.org/abs/astro-ph/9806052) — retained_review_rechecked
- [rodriguez2006](https://arxiv.org/abs/astro-ph/0602235) — new_retrieval
- [chen2013aql](https://arxiv.org/abs/1309.6380) — new_retrieval

## Evidence, temporal correspondence, and conflicts

Rodriguez Table 1 hard-state RXTE observations are P91414 in May 2005 (MJD 53493.77 onward), not selected P91028 on April 4. Chen Table 1 explicitly labels bursts in selected 70069-03-02-03 as soft and 93076-01-09-00 as hard, but the table states state when bursts occurred. Its burst/preburst analysis does not establish the state of all GTIs in the frozen spectra. Retain these as partial-interval provisional evidence, not whole-ObsID assignments. No actual transition is asserted merely because coverage is partial.

No competing admitted native-state assignment was found. Discrepant or incomplete coverage is described above; this is not a claim of universal literature agreement. Full GTI lists were not newly extracted: exact full-pointing native labels or conservative full archive-span containment are required. The field gti_match remains false where no explicit published GTI boundary was joined.

## All selected ObsIDs and dates

| rxte_obsid     | observation_start       | observation_end         | native_state_label   | evidence_level   | common_regime   | eligible_for_confirmatory   |
|:---------------|:------------------------|:------------------------|:---------------------|:-----------------|:----------------|:----------------------------|
| 20098-03-01-00 | 1997-02-16T22:52:33.024 | 1997-02-17T05:06:45.024 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |
| 30073-05-01-00 | 1998-04-10T22:15:55.008 | 1998-04-11T01:23:44.008 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |
| 50049-01-05-01 | 2000-10-07T17:55:07.104 | 2000-10-07T18:57:31.104 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |
| 70069-03-02-03 | 2002-03-14T03:58:39.072 | 2002-03-14T05:33:07.072 | MIXED_OR_TRANSITION  | PROVISIONAL      | UNMAPPED        | False                       |
| 91028-01-01-00 | 2005-04-04T00:06:07.200 | 2005-04-04T01:06:49.200 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |
| 93076-01-09-00 | 2007-05-31T11:52:26.400 | 2007-05-31T13:09:27.400 | MIXED_OR_TRANSITION  | PROVISIONAL      | UNMAPPED        | False                       |
| 94441-01-01-02 | 2009-12-03T19:53:47.328 | 2009-12-03T20:58:02.328 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |
| 96440-01-08-06 | 2011-12-08T02:33:14.688 | 2011-12-08T03:37:44.688 | UNCLASSIFIED         | UNRESOLVED       | UNMAPPED        | False                       |

## Final decision

New observations usable in a common regime: 0; independent hard-regime source gain: 0. Other observations remain unavailable for common matching; original valid labels remain active in the derived catalogue. No source class, proxy value, or classifier prediction was used to assign a state.
