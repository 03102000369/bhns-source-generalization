"""Catalogue reports and one-time preregistration. Run before any new ML fit."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from bhns.data.state_validation import LEVELS,PROXY_FEATURES,usable_states,match_native_cohort,sha256,verify_protected

ROOT=Path(__file__).resolve().parents[1]
REVIEWS={
 '1a_1744_361':(['bhattacharyya2006'],'2003 banana and 2004 AHB are supported; 2005 first pointing may be transitional. Later years unresolved; do not extend outburst labels.'),
 '4u_0614_09':(['ford1997','vanstraaten2000'],'Mendez Table 1 dates are February 26, March 16 and April 13 1996; our first observation is April 22. Color/timing aggregates in van Straaten do not provide an extracted unique state join for our selected ObsIDs.'),
 '4u_1254_69':([], 'Smale et al. 2002 is a candidate referenced by later studies, but the selected observations start in 2004. No secure observation-level state table retrieved. Source-level banana descriptions are insufficient.'),
 '4u_1543_475':(['park2004','russell2020'],'TD, SPL, transition and later hard decay are covered. Park SPL versus Russell SIMS on MJD 52459-52461 is a nomenclature conflict, not established physical disagreement. Conservatively exclude.'),
 '4u_1608_522':(['yu1997'],'Explicit island dates March 15,18,22 1996. Only selected observations contained within those days are labelled; later years require observation-level mapping.'),
 '4u_1636_536':(['belloni2007','altamirano2008'],'The long monitoring and grouped timing studies cover island/banana cycles; group averages and color diagrams need a machine-readable per-ObsID state join. No blanket label for 1998-2011.'),
 '4u_1702_429':(['markwardt1999'],'July 19-30 1997 contains spectral movement between island and lower banana. The selected July 19 pointing cannot securely inherit a unique state from that aggregate description.'),
 '4u_1705_44':(['chen2014'],'Ji et al. study burst-selected island/banana samples. The 2014 unified-model paper identifies P93060 in September-November 2007; neither retrieved screen establishes full-ObsID labels for this selection.'),
 '4u_1728_34':([], 'Zhang et al. 2016 study (MNRAS 455,2004) provides burst-epoch colors and Sa. These are not automatically full-observation states, and its color calibration differs from our 5-25 keV coordinates. Observation/GTI correspondence remains unresolved.'),
 '4u_1735_444':(['lei2013'],'Table 1 provides region IV for 20084-01-02-03. Region-to-upper-banana correspondence is qualified as mainly; record PROVISIONAL. Other selected IDs lack a secure extracted join.'),
 '4u_1746_37':(['jonker2000'],'The 1996/1998 campaign discusses low/high-intensity branches; selected observations start in 2002. Search results contain inconsistent broad descriptions, so no source-wide island label is propagated.'),
 'aql_x_1':(['zhang1998','cui1998'],'1997 transition near MJD 50510-50512 and 1998 snapshots have rapid state changes. The three precisely tabulated 1997 spectral epochs do not match the selected February 16 observation; no visual interpolation assigned.'),
 'cyg_x_2':(['wijnands1999cyg'],'October 31 1996 and September 28-29 1997 campaign: horizontal versus probable normal/flaring states. Secure date overlap with the selected sample not established. Z branch nomenclature kept separate.'),
 'gro_j1655_40':(['shaposhnikov2007'],'2005 early hard interval admitted. September decay, 1996 and other expansion candidates remain unresolved in this bounded review.'),
 'grs_1915_105':(['belloni2000grs'],'Table 1 abbreviation J=20187-02: 20187-02-01-00 is class alpha. A variability class can mix A/B/C states; mark ambiguous for single-state control. Other expansion years unresolved.'),
 'gs_1354_64':(['brocksopp2001'],'Nine analysed ObsIDs directly listed; tenth faint pointing excluded by authors. Later selected archive observations do not inherit 1997 hard labels.'),
 'gx_339_4':(['belloni2005gx'],'High/soft interior MJD 52561-52693 is secure. Other phases require exact table join because SIMS/HIMS transitions recur. CDS ReadMe/table1 retrieval at J/A+A/440/207 returned HTTP404; no table fabricated.'),
 'hete_j1900_1_2455':(['patruno2017'],'Table 1 contains selected ObsIDs but groups are timing-fit groups, not a labelled state catalogue. Explicit island ObsIDs 92049-01-44-00 and 91015-01-06-02 are not selected. No pulsar-type substitution for state.'),
 'igr_j00291_5934':(['falanga2005'],'December 7-10 2004 RXTE campaign and Comptonized spectrum are reviewed. Pulsar identity/continuum fit alone is not assigned as an atoll state; 2008 and later candidates not inferred.'),
 'ks_1731_260':(['muno2000','chen2014'],'Muno Table 1 supplies per-ObsID hard colors; apply only the authors thresholds HC<0.50 banana, HC>0.65 island. Intermediate colors remain unresolved. These describe persistent emission, not burst removal.'),
 'mxb_1658_298':(['sharma2018'],'Retrieved detailed hard/soft study concerns the 2015-2017 outburst, after RXTE. Historical 1999-2001 discussion supplies no admitted observation-level assignment.'),
 'sax_j1750_8_2900':(['kaaret2002'],'Primary Kaaret RXTE study located, but arXiv PDF requests (unversioned and v2) returned HTTP406. Abstract establishes variability, not full-ObsID state assignments; unresolved rather than guessed.'),
 'sax_j1806_5_2215':([], '2011 ATels 3193,3202,3381 and 2012 ATel3926 locate outburst, bursts and Swift continuum evidence. No secure full-ObsID RXTE state mapping; ongoing activity is not a spectral state.'),
 'sax_j1808_4_3658':(['ibragimov2009'],'2002 paper defines peak/slow-decay/rapid-drop/flaring-tail phases and a multicomponent spectrum. Outburst phases are retained as context, not silently renamed island states for this project.'),
 'sax_j1810_8_2609':(['delSanto2008','yang2012'],'Fiocchi explicitly lists 93414-01-04-01; other assignments confined to published IBIS epochs. Zhu whole-outburst hard description corroborates but is not used to fill observing gaps or late decay.'),
 'ser_x_1':(['oosterbroek2001','migliari2004'],'Two dated campaigns admit upper-banana/banana. No extrapolation of its usual soft behavior to the remaining mission years.'),
 'slx_1735_269':(['wijnands1999slx'],'Five selected IDs in Table 1. Authors island interpretation is explicitly tentative and conditioned on atoll classification, so all are PROVISIONAL.'),
 'v404_cyg':([], 'Quiescent optical/X-ray studies located; no selected RXTE spectrum entered the HEASoft expanded cohort. Quiescent source history is not a verified detection or state label for these six candidates.'),
 'v4641_sgr':(['maitra2006'],'Three selected IDs intersect Table 1; dwell 2 is rapidly variable/obscured, excluded from single-state comparison. Stable hard dwells admitted.'),
 'xte_j1118_480':(['brocksopp2010'],'Both outbursts remained low/hard; use conservative 2000 plateau interior and the 2005 Table 1 PCA campaign. Exclude late 2005 tail and 2007 candidate.'),
 'xte_j1550_564':(['belloni2002','sturner2005'],'Bounded 2002 and 2003 hard-only campaign intervals admitted. The 1998/1999 outburst is not labelled from these later papers.'),
 'xte_j1859_226':(['radhika2014'],'Only explicit MJD 51490-51501 SIMS interval admitted. Older very-high/soft terminology is not equated with SIMS or interpolated across the rest of the outburst.'),
}

def main():
 r=ROOT;target=r/'configs/state_validation_protocol_frozen.yaml'
 if target.exists():raise ValueError('Protocol already frozen; do not overwrite')
 cat=pd.read_csv(r/'data/state_validation/obsid_state_catalogue.csv').fillna('')
 refs=json.loads((r/'data/state_validation/literature/curated_references.json').read_text())
 searches=json.loads((r/'data/state_validation/literature_search_log.json').read_text())['searches']
 registry=[]
 for sid,g in cat.groupby('source_id'):
  keys,note=REVIEWS[sid];q=next(x for x in searches if x['source']==sid)
  text=f'# {g.canonical_source.iloc[0]}: state evidence review\n\nSearch query: `{q["q"]}`. Full discovery output is retained in literature_search_log.json. This is a bounded evidence review, not a claim of exhaustive literature coverage.\n\n'
  text+=f'Selected archive coverage: {g.observation_start.min()} to {g.observation_end.max()}; {len(g)} ObsIDs, {int(g.in_expanded.sum())} in expanded HEASoft cohort.\n\n{note}\n\n'
  text+='## Primary manuscripts screened\n\n'
  for key in keys:
   ref=refs[key];text+=f'- [{ref.get("title",ref["arxiv"])}]({ref["url"]}) — {ref.get("authors","bibliographic metadata not retrieved")}; {ref["year"] or "year unverified"} preprint. Retrieval: {ref["status"]}.\n'
   registry.append(dict(source_id=sid,reference_id=key,status='full_text_state_date_and_ID_screen' if ref['status']=='retrieved' else 'abstract_only_retrieval_blocked',review_note=note))
  if not keys:text+='No locally retrieved full manuscript admitted. Search candidates below are discovery records, not state evidence.\n'
  text+='\n## Other search candidates (not assignment evidence)\n\n'
  candidates=[]
  for chunk in str(q['result']).split('--------------------------------------------------------------------------------'):
   first=chunk.strip().split('\n')[0]
   if 'http' in first and len(first)<500:candidates.append(first)
  text+='\n'.join('- '+s for s in candidates[:8])
  text+='\n\n## ObsID mapping and unresolved cases\n\n'+g[['rxte_obsid','observation_start','native_state_label','state_confidence','reference_id','in_expanded']].to_markdown(index=False)+'\n'
  text+='\n## Conflicts\n\n'+('Competing labels retained in state_assignment_claims.csv; CONFLICTED observations excluded.\n' if g.state_confidence.eq('CONFLICTED').any() else 'No competing admitted assignment found in this bounded review. This does not establish agreement throughout the literature.\n')
  (r/'reports/state_validation/sources'/f'{sid}.md').write_text(text)
 pd.DataFrame(registry).to_csv(r/'data/state_validation/literature_review_registry.csv',index=False)
 gates=json.loads((r/'results/state_validation/feasibility.json').read_text());g=gates['expanded'];counts=cat.state_confidence.value_counts()
 states=cat.groupby(['class_label','native_state_label']).agg(observations=('rxte_obsid','size'),physical_sources=('source_id','nunique')).reset_index()
 states.to_csv(r/'results/state_validation/state_distributions.csv',index=False)
 coverage=[]
 for name,frame in [('considered',cat),('primary',cat[cat.in_primary]),('heasoft',cat[cat.in_heasoft]),('expanded',cat[cat.in_expanded])]:
  for cls,c in frame.groupby('class_label'):
   reliable=usable_states(c);coverage.append(dict(cohort=name,class_label=cls,observations=len(c),physical_sources=c.source_id.nunique(),usable_label_observations=len(reliable),usable_label_sources=reliable.source_id.nunique(),**{level:int(c.state_confidence.eq(level).sum()) for level in LEVELS}))
 cov=pd.DataFrame(coverage);cov.to_csv(r/'results/state_validation/catalogue_coverage.csv',index=False)
 report='# State catalogue feasibility\n\nSTATE_GATE = **'+g['STATE_GATE']+'** before any new model fit.\n\n'
 report+='Independent unit: physical source. Minimum is five BH and five NS systems in a shared, justified regime. Native taxonomies remain distinct. DIRECT/STRONG with ambiguous=false are admissible; confidence measures evidence linkage, not certainty of the underlying physics.\n\n'
 report+=cov.to_markdown(index=False)+'\n\nExpanded cohort common-regime support:\n\n'+pd.DataFrame(g['regime_source_counts']).to_markdown(index=False)+'\n\n'
 report+='Hard overlap has six BH but only two NS sources; soft overlap has two BH and one NS. Neither supports confirmatory matching. Native labels are useful descriptively in eight BH and five NS systems, but that total does not fix per-regime scarcity. STATE_MATCHED_V1, cross-state transfer and matched permutations are infeasible. The separately frozen proxy-only diagnostic uses all 213 expanded observations (9 BH/22 NS); it is not a state-matched test.\n\n'
 report+='The 880 selected candidates comprise 858 original acquisition selections and 22 expansion selections. Unselected archive query hits are outside this catalogue. All 687 primary, 207 HEASoft and 213 expanded observations are represented. Archive elapsed duration determines end time; a 120-second boundary guard prevents marginal date matches.\n\n'
 report+='A single literature conflict (Park SPL versus Russell SIMS) is retained. Mixed/transition observations and tentative labels are excluded. Labels refer to persistent-state evidence; no new burst/GTI filtering has been imposed on frozen spectra. No completeness claim is made for sources without labels.\n\n'+states.to_markdown(index=False)+'\n'
 (r/'reports/state_validation/state_catalogue_feasibility.md').write_text(report)
 matched,_=match_native_cohort(cat[cat.in_expanded]);matched.to_csv(r/'data/state_validation/state_matched_observations.csv',index=False)
 mapping=dict(version='STATE_REGIME_MAPPING_V1',native_labels_preserved=True,taxonomy_equivalence_assumed=False,
  assignment_rules_sha256=sha256(r/'data/state_validation/reviewed_assignment_rules.json'),
  common_regimes={'HARD_DOMINATED':'Only evidence-specific claims with explicit hard/Comptonized spectral interpretation; see reviewed rules. No automatic island-to-hard mapping.',
                  'SOFT_DOMINATED':'Evidence-specific BH thermal/high-soft or Ser X-1 soft campaign descriptions. No automatic banana-to-soft mapping.',
                  'UNMAPPED':'All other native categories, unresolved or conflicting evidence.'},
  physical_equivalence_claim=False,matching_status='INFEASIBLE_DUE_TO_SOURCE_COUNT',
  proxies=dict(name='detector_spectral_regime_coordinates_not_physical_states',edges_keV=[5.,5+20*10/43,5+20*21/43,25.],
    bands='sum frozen integrated 43-bin net count rates at indices 0:10,10:21,21:43; signed bins retained',
    features=PROXY_FEATURES,formula='log10(mid/soft), log10(high/mid), log10(soft+mid+high)',
    invalid='Exclude nonfinite or nonpositive band totals without clipping or imputation',
    learned_population_statistics='none',limitations='Detector counts retain gain/response, absorption and distance effects; 5 keV lower boundary misses much thermal disk emission. Intensity is not Eddington-scaled.'))
 (r/'configs/state_regime_mapping.yaml').write_text(json.dumps(mapping,indent=2)+'\n')
 now=datetime.now(timezone.utc).isoformat()
 protocol=dict(version='STATE_VALIDATION_V1',frozen_utc=now,eligible_cohort='frozen EXPANDED_SOURCE (213 observations; 9 BH,22 NS)',
  evidence_levels=['DIRECT','STRONG'],exclusions=['PROVISIONAL','UNRESOLVED','CONFLICTED','ambiguous or mixed pointings'],
  taxonomy='publication-specific native labels; evidence-specific observable regime mappings only',
  mapping_sha256=sha256(r/'configs/state_regime_mapping.yaml'),minimum_physical_sources_per_class_per_regime=5,
  matching=dict(variables=['evidence_specific_common_regime'],tolerance='exact category plus admissible evidence',
    priority=['independent sources','state distribution','detector support','observations'],status='INFEASIBLE_DUE_TO_SOURCE_COUNT',
    continuous_matching='not performed; no empirically tuned caliper or test-source-derived support'),
  primary_analysis=dict(name='STATE_MATCHED_V1',status='NOT_RUN',reason='No shared justified regime with five physical sources per class; new data/new protocol required before matching'),
  secondary_proxy_diagnostic=dict(enabled=True,confirmatory=False,cohort='all expanded observations with positive finite three-band totals',features=PROXY_FEATURES,
    objective='Measure class separation carried by coarse spectral-regime coordinates; not physical-state adjustment or a causal mediation analysis',
    comparator='Reuse frozen EXPANDED_SOURCE full 43-bin predictions on identical ObsIDs and sources; paired bootstrap proxy minus full'),
  models={'logistic':{'solver':'liblinear','C':[.01,.1,1.,10.]},'forest':{'n_estimators':100,'min_samples_leaf':3,'max_depth':[4,None]}},
  splits=['5-fold source-stratified grouped','leave-one-physical-source-out'],inner='20% stratified physical-source holdout within outer training; choose source BA; first candidate wins ties',
  preprocessing='StandardScaler fitted only to inner training during selection and outer training during refit; no imputation, PCA, feature selection or resampling',
  weighting='existing mean-one inverse-observation-count weights: equal total mass per training source; class mass remains proportional to training source counts; no class weighting',
  aggregation='mean clipped log odds across observations per held-out source; NS positive',metrics=['AUROC','balanced_accuracy','MCC','F1','PR_AUC','Brier'],
  threshold=.5,threshold_recalibration='none',calibration='descriptive source reliability in 5 fixed equal-width bins; Brier; prediction probability distributions; no threshold optimization',
  uncertainty='2000 class-stratified physical-source percentile bootstrap draws; conditional on fitted predictions, does not refit models or capture all training variability',
  seed=42,permutations={'planned_if_matched_feasible':50,'unit':'physical source','compare':['observation-wise','source-grouped'],'status':'NOT_RUN_NO_MATCHED_COHORT'},
  cross_state='INFEASIBLE_DUE_TO_SOURCE_COUNT',within_source='Descriptive native-state score summaries; no observation-level significance tests',
  interpretation='No arbitrary success threshold. Assess effect size and uncertainty only for a credible matched design. With current source scarcity, physical-state verdict must remain STATE_INCONCLUSIVE regardless of proxy AUROC.',
  prior_information='Primary and HEASoft results were already known; no state-stage model performance has been computed before this freeze.')
 target.write_text(json.dumps(protocol,indent=2)+'\n')
 ph=sha256(target);(r/'configs/state_validation_protocol_frozen.sha256').write_text(ph+'\n')
 prereg=f'# State-validation preregistration\n\nFrozen at {now}, before the first state-stage ML fit.\n\nProtocol SHA-256: `{ph}`. Mapping SHA-256: `{sha256(r/"configs/state_regime_mapping.yaml")}`.\n\nThe catalogue gate is LIMITED: no confirmatory state-matched spectral experiment, cross-state test or matched permutations may run. Native states and confidence remain frozen. The sole new ML analysis is an exploratory three-coordinate proxy-only diagnostic on the expanded cohort, using the existing LR/RF and source-disjoint evaluation. Its results cannot establish survival after physical-state control. Matching criteria will not be relaxed based on its performance.\n\nAll inputs and analysis code are hashed in results/state_validation/frozen_manifest.json. Downstream reports may be regenerated from those frozen inputs; scientific changes require a versioned addendum.\n'
 (r/'reports/state_validation/preregistration.md').write_text(prereg)
 files=['configs/state_regime_mapping.yaml','configs/state_validation_protocol_frozen.yaml','configs/state_validation_protocol_frozen.sha256','reports/state_validation/preregistration.md','reports/state_validation/state_catalogue_feasibility.md','results/state_validation/feasibility.json','src/bhns/data/state_validation.py','src/bhns/experiments/state_validation.py','scripts/build_state_catalogue.py']
 files+=['scripts/run_state_validation.py','scripts/prepare_state_validation.py']
 files+=['data/state_validation/'+f for f in ['observation_universe.csv','obsid_state_catalogue.csv','state_assignment_claims.csv','reviewed_assignment_rules.json','state_evidence_registry.csv','spectral_regime_coordinates.csv','state_matched_observations.csv']]
 (r/'results/state_validation/frozen_manifest.json').write_text(json.dumps({f:sha256(r/f) for f in files},indent=2))
 print(ph)

if __name__=='__main__':main()
