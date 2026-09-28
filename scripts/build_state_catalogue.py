"""Reproduce the reviewed evidence catalogue; never reads model predictions."""
import json,re
from pathlib import Path
import pandas as pd
from astropy.time import Time
from bhns.data.state_validation import contained,resolve_claims,regime_feasibility,sha256,verify_protected

ROOT=Path(__file__).resolve().parents[1]
def main():
 root=ROOT; verify_protected(root,json.loads((root/'results/state_validation/protected_artifact_manifest.json').read_text()))
 u=pd.read_csv(root/'data/state_validation/observation_universe.csv');lib=root/'data/state_validation/literature'
 refs={r['reference_id']:r for r in json.loads((lib/'references.json').read_text())}
 refs['ford1997'].update(title='Kilohertz QPO and Atoll Source States in 4U 0614+09',authors='M. Mendez; M. van der Klis; J. van Paradijs; W.H.G. Lewin; F.K. Lamb; B.A. Vaughan; E. Kuulkers; D. Psaltis',date='1997/05/30')
 refs['markwardt1999'].update(title='Observation of Kilohertz Quasiperiodic Oscillations from the Atoll Source 4U 1702-429',authors='Craig B. Markwardt; Tod E. Strohmayer; Jean H. Swank',date='1998/12/27')
 for ref in refs.values():
  ref['year']=int(ref.get('date','0')[:4]);ref['url']='https://arxiv.org/abs/'+ref['arxiv'];ref['year_basis']='arXiv first submission; reference_id is a stable key, not a date field'
 claims=[];rules=[]
 def add(sid,ref,label,family,taxonomy,notes,ids=None,window=None,level=None,ambiguous=False,regime='UNMAPPED',prefix=None,method=None):
  lev=level or ('DIRECT' if ids else 'STRONG');lo=hi=None
  if window:
   lo,hi=[float(Time(x,format='isot',scale='utc').mjd) if isinstance(x,str) else float(x) for x in window]
  rule=dict(source_id=sid,reference_id=ref,native_state_label=label,state_family=family,source_state_taxonomy=taxonomy,notes=notes,obsids=ids or [],window_mjd=[lo,hi],state_confidence=lev,ambiguous=ambiguous,common_regime=regime,prefix=prefix)
  rules.append(rule)
  for row in u[u.source_id.eq(sid)].to_dict('records'):
   direct=ids is not None and row['rxte_obsid'] in ids
   date_match=window is not None and contained(row['start_mjd'],row['end_mjd'],lo,hi)
   if ids is not None and not direct:continue
   if window is not None and not date_match:continue
   if prefix and not row['rxte_obsid'].startswith(prefix):continue
   claims.append(dict(rxte_obsid=row['rxte_obsid'],source_id=sid,reference_id=ref,native_state_label=label,state_family=family,
    source_state_taxonomy=taxonomy,notes=notes,state_confidence=lev,ambiguous=ambiguous,common_regime=regime,
    state_assignment_method=method or ('explicit_ObsID' if direct else 'full_span_publication_interval'),
    obsid_directly_listed=direct,date_window_match=date_match,
    evidence_time_start='' if lo is None else Time(lo,format='mjd').isot,evidence_time_end='' if hi is None else Time(hi,format='mjd').isot))
 # Reviewed primary tables and explicit statements. None of these rules use ML output.
 ids=re.findall(r'\b\d{5}-\d{2}-\d{2}-\d{2}\b',(lib/'brocksopp2001.txt').read_text())
 add('gs_1354_64','brocksopp2001','BH_LOW_HARD','BH_HARD','Brocksopp low/hard',
  'Table 1 contains nine analysed pointings; Section 3 identifies the entire analysed outburst as low/hard. Excludes the unanalysed tenth pointing and later quiescent years.',ids=sorted(set(ids)),regime='HARD_DOMINATED')
 for bounds in [('2000-03-29','2000-08-01'),(53383,53404)]:
  add('xte_j1118_480','brocksopp2010','BH_LOW_HARD','BH_HARD','Brocksopp low/hard',
   'Abstract and Section 1.1 identify both outbursts as low/hard. Conservative interior of the 2000 plateau; 2005 bounded by PCA campaign in Table 1. No extrapolation to 2007.',window=bounds,regime='HARD_DOMINATED')
 for lo,hi in [(52442,52456),(52462,52474)]:
  add('4u_1543_475','park2004','BH_THERMAL_DOMINANT','BH_SOFT','Park TD/SPL/hard',
   'Section 3.3: thermal-dominant intervals; integer endpoint denotes the whole published MJD day. Native TD retained.',window=(lo,hi),regime='SOFT_DOMINATED')
 for lo,hi in [(52456,52459),(52474,52478)]:
  add('4u_1543_475','park2004','BH_TRANSITION','BH_TRANSITION','Park TD/SPL/hard',
   'Section 3.3: transition and developing band-limited noise during final monitoring days; not a stable hard state.',window=(lo,hi),ambiguous=True)
 add('4u_1543_475','park2004','BH_STEEP_POWER_LAW','BH_SPL','Park TD/SPL/hard','Section 3.3: SPL on MJD 52459-52461.',window=(52459,52462))
 add('4u_1543_475','russell2020','BH_SOFT_INTERMEDIATE','BH_SIM','Belloni taxonomy used by Russell',
  'Section 3.2 associates MJD 52459-52461 type-B QPO observations with SIMS. Nomenclature conflicts with Park SPL; both retained, no equivalence imposed.',window=(52459,52462))
 add('4u_1543_475','russell2020','BH_HARD','BH_HARD','Belloni taxonomy used by Russell',
  'Section 4 and Figure 5: hard-state transition completed by MJD 52483; restrict to clearly plotted decay through MJD 52510. These are newly reviewed labels, not changes to old annotations.',window=(52484,52510),regime='HARD_DOMINATED')
 add('v4641_sgr','maitra2006','BH_LOW_HARD','BH_HARD','Maitra canonical low/hard',
  'Table 1 dwells 1,3,4 and Section 2: hard Comptonized spectra. Obscured variable dwell 2 is handled separately.',ids=['80054-08-01-00','80054-08-02-00','80054-08-02-01'],regime='HARD_DOMINATED')
 add('v4641_sgr','maitra2006','BH_MIXED_OBSCURED','BH_MIXED','Maitra obscured dwell',
  'Table 1 dwell 2 has rapid obscuration/spectral changes and a hidden hot disc interpretation. Full ObsID cannot be treated as one stable state.',ids=['80054-08-01-01'],ambiguous=True)
 add('gro_j1655_40','shaposhnikov2007','BH_LOW_HARD','BH_HARD','Shaposhnikov LHS/IS/HSS',
  'Section 3.1.1 specifies MJD 53418-53435 LHS; end truncated before transition day 53435.',window=(53418,53435),regime='HARD_DOMINATED')
 add('gx_339_4','belloni2005gx','BH_HIGH_SOFT','BH_SOFT','Belloni four-state',
  'Table 1 and high/soft section: observations 110-148 span MJD 52560.41-52693.73. Conservative interior excludes endpoints and transition days.',window=(52561,52693),regime='SOFT_DOMINATED')
 add('grs_1915_105','belloni2000grs','BH_GRS_CLASS_ALPHA','BH_GRS_VARIABILITY','Belloni GRS variability class / A-B-C',
  'Table 1 J-01-00 expands to 20187-02-01-00; all intervals class alpha. This combines distinct A/B/C states and is excluded from single-state matching.',ids=['20187-02-01-00'],ambiguous=True)
 add('xte_j1550_564','belloni2002','BH_LOW_HARD','BH_HARD','Belloni low/hard',
  'All eleven Table 1 observations in January 2002 are low/hard; match full spans inside analysed campaign, excluding February tail.',window=('2002-01-10','2002-02-01'),regime='HARD_DOMINATED')
 add('xte_j1550_564','sturner2005','BH_LOW_HARD','BH_HARD','Sturner low/hard',
  'Sections 2-3: failed hard outburst; conservative simultaneous INTEGRAL campaign March 27-April 12 2003, not entire spring.',window=('2003-03-27','2003-04-13'),regime='HARD_DOMINATED')
 add('xte_j1859_226','radhika2014','BH_SOFT_INTERMEDIATE','BH_SIM','Radhika four-state',
  'Section 3.1.3 explicitly discusses MJD 51490-51501 as soft-intermediate despite a hard-looking photon index. Restrict to this interval; other phases not digitized.',window=(51490,51502))
 # NS taxonomy is preserved. Banana/island is never automatically equated with BH soft/hard.
 add('1a_1744_361','bhattacharyya2006','NS_ATOLL_BANANA','NS_ATOLL_BANANA','Bhattacharyya atoll/AHB',
  'Section 2: all analysed P80431 2003 observations on banana branch. Year is a campaign filter, not a claim about unobserved days.',window=('2003-01-01','2004-01-01'),prefix='80431',method='published_proposal_and_year_scope')
 add('1a_1744_361','bhattacharyya2006','NS_ATOLL_BANANA','NS_ATOLL_BANANA','Bhattacharyya atoll/AHB',
  'Figure 3 and Table 1 representative 2003 banana observation.',ids=['80431-01-02-04'])
 add('1a_1744_361','bhattacharyya2006','NS_ATOLL_AHB_LOW_HARD','NS_ATOLL_AHB','Bhattacharyya atoll/AHB',
  'Section 2 explicitly identifies both 2004 ObsIDs as low-hard AHB; Section 3 finds no blackbody required. AHB is not renamed Z horizontal branch or extreme island.',ids=['90058-04-01-00','90058-04-02-00'],regime='HARD_DOMINATED')
 for day in ['1996-03-15','1996-03-18','1996-03-22']:
  lo=Time(day).mjd
  add('4u_1608_522','yu1997','NS_ATOLL_ISLAND','NS_ATOLL_ISLAND','Yu island/banana',
   'Table 1 and results identify the three March 1996 observing days as island. Low-intensity hard power-law regime is explicitly discussed; no extension to later outbursts.',window=(lo,lo+1),regime='HARD_DOMINATED')
 # Published diagnostic, not our PCA counts: HC thresholds are specific to Muno's Table 1.
 for line in (lib/'muno2000.txt').read_text().splitlines():
  m=re.match(r'^(\d{5}-\d{2}-\d{2}-\d{2})\s+199[6789].*\s(0\.\d+)\s*$',line.strip())
  if not m:continue
  oid,hc=m.group(1),float(m.group(2));state='ISLAND' if hc>.65 else 'BANANA' if hc<.50 else None
  if state:
   add('ks_1731_260','muno2000','NS_ATOLL_'+state,'NS_ATOLL_'+state,'Muno published color/timing criteria',
    f'Table 1 published hard color {hc:g}; Section 2.1 criterion HC>0.65 island, HC<0.50 banana. Published diagnostic, not model-derived; persistent emission state, bursts require separate screening.',ids=[oid],level='STRONG',method='published_ObsID_color_and_author_state_threshold')
 add('slx_1735_269','wijnands1999slx','NS_ATOLL_ISLAND','NS_ATOLL_ISLAND','Wijnands tentative island',
  'Table 1 matches; Section 3 explicitly qualifies island assignment as a suggestion conditional on atoll identity. Retain as PROVISIONAL.',ids=sorted(set(re.findall(r'\b\d{5}-\d{2}-\d{2}-\d{2}\b',(lib/'wijnands1999slx.txt').read_text()))),level='PROVISIONAL')
 add('sax_j1810_8_2609','delSanto2008','NS_LOW_HARD','NS_LOW_HARD','Fiocchi low/hard',
  'Table 1 epoch 5 explicitly names PCA ObsID and hard thermal-Comptonization analysis.',ids=['93414-01-04-01'],regime='HARD_DOMINATED')
 for lo,hi in [(54337,54358),(54358,54363),(54367,54371),(54373,54377)]:
  add('sax_j1810_8_2609','delSanto2008','NS_LOW_HARD','NS_LOW_HARD','Fiocchi low/hard',
   'Table 1 IBIS epoch and discussion support low/hard emission. STRONG interval containment, not simultaneous pointed PCA except epoch 5. Gaps and late decay excluded.',window=(lo,hi),regime='HARD_DOMINATED')
 add('ser_x_1','oosterbroek2001','NS_ATOLL_UPPER_BANANA','NS_ATOLL_BANANA','Oosterbroek atoll banana',
  'Sections 2 and 4: September 5 1999 simultaneous RXTE/BeppoSAX observation in upper banana, with soft spectral components and low electron temperature. Calendar day is the secure scope.',window=('1999-09-05','1999-09-06'),regime='SOFT_DOMINATED')
 add('ser_x_1','migliari2004','NS_ATOLL_BANANA','NS_ATOLL_BANANA','Migliari banana',
  'Table 1 MJD 52421 simultaneous campaign and Figure 2: explicitly soft banana state. No extrapolation to other Ser X-1 dates.',window=(52421,52422),regime='SOFT_DOMINATED')
 add('4u_1735_444','lei2013','NS_ATOLL_UPPER_BANANA','NS_ATOLL_BANANA','Lei CCD regions I-IV',
  'Table 1 identifies ObsID in region IV; Section 3 maps region IV mainly to upper banana. PROVISIONAL because region/state correspondence is qualified.',ids=['20084-01-02-03'],level='PROVISIONAL')
 # Collapse redundant evidence from the same reference (an explicit ObsID supersedes its broad scope).
 c=pd.DataFrame(claims);c['rank']=c.state_confidence.map({'DIRECT':0,'STRONG':1,'PROVISIONAL':2})
 c=c.sort_values('rank').drop_duplicates(['rxte_obsid','reference_id','native_state_label']).drop(columns='rank')
 out=resolve_claims(u,c,refs)
 out.to_csv(root/'data/state_validation/obsid_state_catalogue.csv',index=False)
 c.to_csv(root/'data/state_validation/state_assignment_claims.csv',index=False)
 (root/'data/state_validation/reviewed_assignment_rules.json').write_text(json.dumps(rules,indent=2))
 (lib/'curated_references.json').write_text(json.dumps(refs,indent=2))
 registry=[]
 for ref,group in c.groupby('reference_id'):
  rr=refs[ref]; registry.append(dict(reference_id=ref,source=';'.join(sorted(group.source_id.unique())),citation=rr['authors']+' ('+str(rr['year'])+'). '+rr['title'],doi_or_arxiv=rr['arxiv'],url=rr['url'],state_taxonomy=';'.join(sorted(group.source_state_taxonomy.unique())),evidence_type=';'.join(sorted(group.state_assignment_method.unique())),obsids_or_date_range=';'.join(sorted(group.rxte_obsid.unique())),notes='All competing claims retained in state_assignment_claims.csv; year is preprint year.',local_path=rr.get('path',''),sha256=rr.get('sha256','')))
 pd.DataFrame(registry).to_csv(root/'data/state_validation/state_evidence_registry.csv',index=False)
 gates={name:regime_feasibility(out if name=='considered' else out[out['in_'+name]]) for name in ['considered','primary','heasoft','expanded']}
 (root/'results/state_validation/feasibility.json').write_text(json.dumps(gates,indent=2))
 print(out.state_confidence.value_counts().to_dict());print(json.dumps(gates,indent=2))

if __name__=='__main__':main()
