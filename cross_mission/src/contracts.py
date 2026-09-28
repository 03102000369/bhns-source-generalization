"""Phase-II contracts, usable before any scientific classifier is fitted."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from evidence import sha256

FEATURES={
 'A': ('logF_5_8','logF_8_12','logF_12_18','logF_18_25'),
 'B': ('fraction_5_8','fraction_8_12','fraction_12_18','fraction_18_25'),
 'C': ('logH_mid_soft','logH_high_mid','logF_5_25'),
}

def canonicalize(name, alias_map):
    from census import key
    normalized=key(name)
    if normalized not in alias_map:raise ValueError('Unresolved physical source: '+name)
    values=alias_map[normalized]
    if not isinstance(values,str) or not values:raise ValueError('Conflicting or empty canonical identity')
    return values

def make_folds(identity_rows, train_mission='RXTE', target_mission='NuSTAR', n_folds=5, seed=42):
    """Accept identity columns ONLY: target class cannot affect allocation."""
    required={'mission','obsid','physical_source'}
    if set(identity_rows.columns)!=required:raise ValueError('Fold allocator accepts identity columns only')
    if train_mission==target_mission:raise ValueError('Use a separate within-mission split contract')
    if identity_rows[list(required)].isna().any().any():raise ValueError('Missing identity')
    if identity_rows.duplicated(['mission','obsid']).any():raise ValueError('Duplicate observation identity')
    sources=sorted(set(identity_rows.loc[identity_rows.mission.eq(target_mission),'physical_source']),key=lambda s:hashlib.sha256(f'{seed}|{s}'.encode()).hexdigest())
    if len(sources)<n_folds or n_folds<2:raise ValueError('Insufficient test sources')
    folds=[]
    for index in range(n_folds):
        test_sources=sorted(sources[index::n_folds])
        train=identity_rows[identity_rows.mission.eq(train_mission)&~identity_rows.physical_source.isin(test_sources)]
        test=identity_rows[identity_rows.mission.eq(target_mission)&identity_rows.physical_source.isin(test_sources)]
        fold=dict(fold_id=index,train_mission=train_mission,target_mission=target_mission,test_sources=test_sources,train_sources=sorted(set(train.physical_source)),train_obsids=sorted(train.obsid),test_obsids=sorted(test.obsid))
        validate_fold(fold,identity_rows);folds.append(fold)
    assigned=[s for f in folds for s in f['test_sources']]
    if sorted(assigned)!=sorted(sources):raise ValueError('Incomplete or repeated test-source assignment')
    return folds

def validate_fold(fold, rows):
    if set(fold['train_sources'])&set(fold['test_sources']):raise ValueError('Physical-source overlap')
    tr=rows[rows.mission.eq(fold['train_mission'])&rows.obsid.isin(fold['train_obsids'])]
    te=rows[rows.mission.eq(fold['target_mission'])&rows.obsid.isin(fold['test_obsids'])]
    if len(tr)!=len(fold['train_obsids']) or len(te)!=len(fold['test_obsids']):raise ValueError('Mission/observation mismatch')
    if not len(tr) or not len(te):raise ValueError('Empty fold')
    if set(tr.physical_source)!=set(fold['train_sources']) or set(te.physical_source)!=set(fold['test_sources']):raise ValueError('Source manifest mismatch')
    if set(tr.physical_source)&set(te.physical_source):raise ValueError('Source leakage')
    expected=rows[rows.mission.eq(fold['target_mission'])&rows.physical_source.isin(fold['test_sources'])]
    if set(expected.obsid)!=set(te.obsid):raise ValueError('Incomplete physical test system')
    expected_train=rows[rows.mission.eq(fold['train_mission'])&~rows.physical_source.isin(fold['test_sources'])]
    if set(expected_train.obsid)!=set(tr.obsid):raise ValueError('Unexpected training row selection')

def fit_scaler(training_rows, representation, expected_mission, allowed_sources):
    if set(training_rows.mission)!={expected_mission}:raise ValueError('Target mission entered scaler fitting')
    if not set(training_rows.physical_source)<=set(allowed_sources):raise ValueError('Held-out source entered scaler fitting')
    columns=FEATURES[representation]
    if not np.isfinite(training_rows[list(columns)].to_numpy()).all():raise ValueError('Nonfinite features')
    # Equal source weights also prevent heavily sampled systems setting the mean.
    weights=1/training_rows.groupby('physical_source').physical_source.transform('size').to_numpy()
    scaler=StandardScaler().fit(training_rows[list(columns)],sample_weight=weights)
    return scaler,dict(fit_mission=expected_mission,fit_sources=sorted(set(training_rows.physical_source)),fit_obsids=sorted(training_rows.obsid),feature_columns=list(columns),mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist())

def select_hyperparameters(candidate_scores, tuning_rows, expected_mission, outer_test_sources):
    if set(tuning_rows.mission)!={expected_mission}:raise ValueError('Target mission in hyperparameter selection')
    if set(tuning_rows.physical_source)&set(outer_test_sources):raise ValueError('Test source in hyperparameter selection')
    scores=np.array([x['inner_source_auroc'] for x in candidate_scores],float)
    if not len(scores) or not np.isfinite(scores).all():raise ValueError('Undefined inner validation score')
    return candidate_scores[int(np.argmax(scores))]['parameters']

def representations(fluxes):
    f=np.asarray(fluxes,float)
    if f.ndim!=2 or f.shape[1]!=4 or not np.isfinite(f).all() or (f<=0).any():raise ValueError('Four finite positive observed band fluxes required')
    total=f.sum(axis=1)
    return {'A':np.log10(f),'B':f/total[:,None],'C':np.column_stack((np.log10(f[:,1]/f[:,0]),np.log10(f[:,3]/f[:,2]),np.log10(total)))}

def source_scores(rows):
    if rows.groupby('physical_source').label.nunique().gt(1).any():raise ValueError('Inconsistent physical-source class')
    if rows.duplicated(['mission','obsid']).any():raise ValueError('Duplicate predictions')
    p=np.asarray(rows.p_ns,float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid probability')
    tmp=rows.copy();p=np.clip(p,1e-7,1-1e-7);tmp['logodds']=np.log(p/(1-p))
    out=tmp.groupby('physical_source',sort=True).agg(label=('label','first'),logodds=('logodds','mean'),observations=('obsid','size')).reset_index()
    out['p_ns']=1/(1+np.exp(-out.logodds));out['prediction']=(out.p_ns>=.5).astype(int)
    return out

def bootstrap_indices(source_table, seed=42, repeats=2000):
    if source_table.physical_source.duplicated().any():raise ValueError('Bootstrap input must contain one row per system')
    groups=[np.flatnonzero(source_table.label.to_numpy()==v) for v in (0,1)]
    if min(map(len,groups))<2:raise ValueError('Insufficient independent systems for bootstrap')
    rng=np.random.default_rng(seed)
    return [np.concatenate([rng.choice(g,len(g),replace=True) for g in groups]) for _ in range(repeats)]

def random_source_labels(physical_sources, seed):
    rng=np.random.default_rng(seed)
    return dict(zip(sorted(set(physical_sources)),rng.integers(0,2,len(set(physical_sources))).tolist()))

def require_both_modules(module_records):
    if set(module_records)!={'FPMA','FPMB'}:raise ValueError('Both modules need explicit records')
    for module,record in module_records.items():
        if record['status']!='COMPLETE':raise ValueError(f'{module} not accepted: '+record['status'])

def validate_product_set(paths, obsid, module):
    """Verify OGIP identity and paired response provenance before any fitting."""
    from astropy.io import fits
    if set(paths)!={'source','background','arf','rmf'}:raise ValueError('Incomplete product set')
    hashes={k:sha256(v) for k,v in paths.items()}
    with fits.open(paths['source']) as sh,fits.open(paths['background']) as bh,fits.open(paths['arf']) as ah,fits.open(paths['rmf']) as rh:
        s=sh['SPECTRUM'];b=bh['SPECTRUM'];a=ah['SPECRESP'];e=rh['EBOUNDS'];m=rh['MATRIX']
        for spectrum in (s,b):
            for key,value in [('TELESCOP','NuSTAR'),('INSTRUME',module),('OBS_ID',obsid)]:
                if str(spectrum.header.get(key,'')).upper()!=str(value).upper():raise ValueError('PHA identity mismatch '+key)
            if float(spectrum.header.get('EXPOSURE',0))<=0:raise ValueError('Nonpositive exposure')
            for key in ('BACKSCAL','AREASCAL'):
                if float(spectrum.header.get(key,1))<=0:raise ValueError('Invalid '+key)
        if not np.array_equal(s.data['CHANNEL'],b.data['CHANNEL']):raise ValueError('Source/background channel mismatch')
        if not np.array_equal(s.data['CHANNEL'],e.data['CHANNEL']):raise ValueError('Response channel mismatch')
        if not (float(e.data['E_MIN'].min())<=5 and float(e.data['E_MAX'].max())>=25):raise ValueError('Missing common energy coverage')
        if not np.isfinite(a.data['SPECRESP']).all() or np.max(a.data['SPECRESP'])<=0:raise ValueError('Invalid ARF')
        if len(a.data)!=len(m.data):raise ValueError('ARF/RMF grid mismatch')
        if not np.allclose(a.data['ENERG_LO'],m.data['ENERG_LO']) or not np.allclose(a.data['ENERG_HI'],m.data['ENERG_HI']):raise ValueError('ARF/RMF energies mismatch')
        for key,kind in [('BACKFILE','background'),('ANCRFILE','arf'),('RESPFILE','rmf')]:
            value=s.header.get(key,'')
            if not value or Path(value).name!=Path(paths[kind]).name:raise ValueError('PHA reference mismatch '+key)
        for response in (a,m):
            if str(response.header.get('TELESCOP','')).upper()!='NUSTAR' or response.header.get('INSTRUME')!=module:raise ValueError('Wrong response instrument')
        return dict(obsid=obsid,module=module,sha256=hashes,exposure=float(s.header['EXPOSURE']),background_exposure=float(b.header['EXPOSURE']),channels=len(s.data),caldb_versions=[a.header.get('CALDBVER'),m.header.get('CALDBVER')])

def require_measurement_freeze(root):
    root=Path(root)
    if not (root/'configs/common_representation_frozen.yaml').is_file():raise ValueError('X2 measurement freeze absent; scientific ML forbidden')
    record=json.loads((root/'configs/measurement_freeze.json').read_text())
    if record.get('status')!='VALIDATED' or record.get('performance_started') is not False:raise ValueError('Invalid freeze chronology')
    if sha256(root/'configs/common_representation_frozen.yaml')!=record['sha256']:raise ValueError('Measurement protocol changed after freeze')
    return record
