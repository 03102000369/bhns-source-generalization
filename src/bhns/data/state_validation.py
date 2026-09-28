"""Evidence resolution and nonphysical spectral coordinates for the state stage."""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd

LEVELS = ('DIRECT', 'STRONG', 'PROVISIONAL', 'UNRESOLVED', 'CONFLICTED')
PROXY_FEATURES = ['log_hardness_mid_soft', 'log_hardness_high_mid', 'log_intensity']
SPECTRAL_FEATURES = [f'spectrum_{i:02}' for i in range(43)]
REQUIRED = ['rxte_obsid','canonical_source','class_label','observation_start','observation_end',
 'native_state_label','state_family','state_evidence_level','state_assignment_method',
 'reference_id','reference_title','reference_authors','reference_year','reference_identifier_or_url',
 'evidence_time_start','evidence_time_end','obsid_directly_listed','date_window_match',
 'source_state_taxonomy','state_confidence','ambiguous','notes']

def sha256(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_protected(root, manifest):
 bad=[p for p,h in manifest.items() if not (Path(root)/p).is_file() or sha256(Path(root)/p)!=h]
 if bad: raise ValueError('STOP: protected artifact mismatch: '+', '.join(bad))
 return len(manifest)

def contained(start,end,lower,upper,guard_seconds=120):
 """Full observation span inside half-open evidence interval, with boundary guard."""
 vals=np.array([start,end,lower,upper],float)
 return bool(np.isfinite(vals).all() and end>start and lower<upper
             and start-guard_seconds/86400 >= lower and end+guard_seconds/86400 < upper)

def resolve_claims(universe, claims, references):
 """Keep one row per ObsID; retain every competing claim separately."""
 if universe.rxte_obsid.duplicated().any():raise ValueError('Duplicate universe ObsID')
 if claims.duplicated(['rxte_obsid','reference_id','native_state_label']).any():
  raise ValueError('Duplicate ObsID-state evidence')
 if not set(claims.state_confidence)<=set(LEVELS[:3]):raise ValueError('Invalid evidence level')
 if not set(claims.reference_id)<=set(references):raise ValueError('Missing reference')
 rows=[]
 for row in universe.to_dict('records'):
  c=claims[claims.rxte_obsid.eq(row['rxte_obsid'])];row.update({k:'' for k in REQUIRED if k not in row})
  row.update(native_state_label='UNCLASSIFIED',state_family='UNCLASSIFIED',state_evidence_level='UNRESOLVED',
   state_confidence='UNRESOLVED',ambiguous=False,obsid_directly_listed=False,date_window_match=False,
   state_assignment_method='no_secure_observation_match',common_regime='UNMAPPED',
   notes='No secure state assignment in the reviewed evidence; not proof that none exists.')
  if len(c):
   conflict=c.native_state_label.nunique()>1;best=c.assign(rank=c.state_confidence.map({v:i for i,v in enumerate(LEVELS)})).sort_values('rank').iloc[0]
   for k in ['native_state_label','state_family','state_assignment_method','source_state_taxonomy','state_confidence','evidence_time_start','evidence_time_end','common_regime']:
    row[k]=best[k]
   row['reference_id']=';'.join(sorted(c.reference_id.unique()))
   for dest,src in [('reference_title','title'),('reference_authors','authors'),('reference_year','year'),('reference_identifier_or_url','url')]:
    row[dest]='; '.join(str(references[r][src]) for r in sorted(c.reference_id.unique()))
   row['notes']=' | '.join(dict.fromkeys(c.notes));row['obsid_directly_listed']=bool(c.obsid_directly_listed.any());row['date_window_match']=bool(c.date_window_match.any())
   row['ambiguous']=conflict or bool(c.ambiguous.any());row['state_evidence_level']=row['state_confidence']
   if conflict:
    row.update(native_state_label='CONFLICTED',state_confidence='CONFLICTED',state_evidence_level='CONFLICTED',
     common_regime='UNMAPPED',state_family='CONFLICTED',notes='Competing native labels: '+';'.join(sorted(c.native_state_label.unique()))+' | '+row['notes'])
  rows.append(row)
 out=pd.DataFrame(rows);validate_catalogue(out);return out

def validate_catalogue(frame):
 missing=set(REQUIRED)-set(frame)
 if missing:raise ValueError('Missing catalogue fields: '+str(missing))
 if frame.rxte_obsid.duplicated().any():raise ValueError('Duplicate ObsID')
 if not set(frame.state_confidence)<=set(LEVELS):raise ValueError('Invalid evidence level')
 if not frame.state_evidence_level.eq(frame.state_confidence).all():raise ValueError('Inconsistent confidence')
 labelled=~frame.state_confidence.eq('UNRESOLVED')
 if frame.loc[labelled,'reference_id'].fillna('').eq('').any():raise ValueError('Unreferenced state')
 if (~frame.loc[frame.state_confidence.eq('CONFLICTED'),'ambiguous']).any():raise ValueError('Conflict must be ambiguous')

def usable_states(frame):
 return frame[frame.state_confidence.isin(['DIRECT','STRONG']) & ~frame.ambiguous]

def regime_feasibility(frame,minimum=5):
 reliable=usable_states(frame);counts=[]
 for regime,g in reliable[reliable.common_regime.ne('UNMAPPED')].groupby('common_regime'):
  n=g.groupby('class_label').source_id.nunique();counts.append(dict(regime=regime,BH=int(n.get('BH',0)),NS=int(n.get('NS',0))))
 passed=[r['regime'] for r in counts if min(r['BH'],r['NS'])>=minimum]
 byclass=reliable.groupby('class_label').source_id.nunique()
 gate='PASS' if passed else 'LIMITED' if min(byclass.get('BH',0),byclass.get('NS',0))>=3 else 'FAIL'
 return dict(STATE_GATE=gate,minimum_sources_per_class_regime=minimum,regime_source_counts=counts,eligible_regimes=passed,
  labelled_BH_sources=int(byclass.get('BH',0)),labelled_NS_sources=int(byclass.get('NS',0)))

def match_native_cohort(frame,minimum=5):
 gate=regime_feasibility(frame,minimum)
 if gate['STATE_GATE']!='PASS':return frame.iloc[:0].copy(),gate
 reliable=usable_states(frame)
 return reliable[reliable.common_regime.isin(gate['eligible_regimes'])].copy(),gate

def spectral_coordinates(frame):
 """Fixed disjoint detector bands; no labels, cohort statistics or fitted cutoffs."""
 x=frame[SPECTRAL_FEATURES].to_numpy(float)
 # Equal bins over 5--25 keV. Sum integrated bin rates; no clipping negative bins.
 bands=np.column_stack([x[:,:10].sum(1),x[:,10:21].sum(1),x[:,21:].sum(1)])
 valid=np.isfinite(bands).all(1)&(bands>0).all(1)
 out=frame[['rxte_obsid','source_id','canonical_source','class_label']].copy()
 out['proxy_valid']=valid;out['intensity']=bands.sum(1)
 out['hardness_mid_soft']=np.where(valid,bands[:,1]/bands[:,0],np.nan)
 out['hardness_high_mid']=np.where(valid,bands[:,2]/bands[:,1],np.nan)
 with np.errstate(invalid='ignore',divide='ignore'):
  for raw in ['hardness_mid_soft','hardness_high_mid','intensity']:out['log_'+raw]=np.where(valid,np.log10(out[raw]),np.nan)
 return out

def feature_matrix(frame,columns):
 if list(columns) not in (PROXY_FEATURES,SPECTRAL_FEATURES):raise ValueError('Unregistered feature family; native class-specific labels prohibited')
 x=frame[list(columns)].to_numpy(float)
 if not np.isfinite(x).all():raise ValueError('Nonfinite features')
 return x
