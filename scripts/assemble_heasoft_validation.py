"""Admit only verified independently reduced products after acquisition terminates."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from bhns.data.instrument_validation import *
ROOT=Path(__file__).resolve().parents[1]

def main():
    verify_primary(ROOT);_,ph=validation_protocol(ROOT)
    primary=pd.read_csv(ROOT/'data/processed/validation_heasoft/preselected_observations.csv')
    expanded=pd.read_csv(ROOT/'data/processed/validation_heasoft/expanded_selection.csv')
    selections=pd.concat([primary.assign(origin='PRIMARY_29'),expanded.assign(origin='EXPANDED')],ignore_index=True)
    rows=[];excluded=[];pending=[]
    for r in selections.to_dict('records'):
        obs=r['rxte_obsid'];folder=ROOT/'data/processed/validation_heasoft/reduction'/obs;path=folder/'processing.json'
        rawpath=ROOT/'data/provenance/validation_heasoft/raw'/obs/'download_manifest.json'
        if not path.exists():
            if rawpath.exists() and json.loads(rawpath.read_text())['status']=='FAILED':excluded.append({**r,'reason':'ARCHIVE_ACQUISITION_FAILED'});continue
            pending.append(obs);continue
        rec=json.loads(path.read_text())
        if rec['status']!='COMPLETE':excluded.append({**r,'reason':rec.get('error',rec['status'])});continue
        if rec['protocol_sha256']!=ph:raise ValueError('Reduction protocol mismatch')
        if any(sha256(folder/p)!=h for p,h in rec['outputs'].items()):raise ValueError('Reduction product changed')
        if rec['caldb_manifest_sha256']!=sha256(ROOT/'results/validation_heasoft/caldb_installation.json'):raise ValueError('CALDB changed')
        arrays,meta=heasoft_spectrum(folder/'source.pha',folder/'background.pha',folder/'response.rsp')
        if not rec['metadata']['deadapp']:raise ValueError('HEASoft did not record deadtime application')
        with np.load(folder/'native.npz') as stored:
            for k in ['spectrum','error','covariance']:np.testing.assert_allclose(arrays[k],stored[k],rtol=1e-12,atol=1e-12)
        row={k:r[k] for k in ['rxte_obsid','source_id','canonical_source','class_label','observation_time','origin']}
        row.update(exposure=meta['exposure'],source_count_rate=meta['source_count_rate'],background_count_rate=meta['background_count_rate'],net_count_rate=meta['net_count_rate'],background_fraction=meta['background_count_rate']/meta['source_count_rate'],gain_epoch=gain_epoch(r['observation_time']),selected_pcus='2',representation='HEASOFT_CALDB_RATE43_V1',errors_available=True,deadtime_status='HEASOFT_CORRECTED',provenance_path=str(path.relative_to(ROOT)),provenance_sha256=sha256(path),native_path=str((folder/'native.npz').relative_to(ROOT)),native_sha256=sha256(folder/'native.npz'),transformation_code_sha256=sha256(ROOT/'src/bhns/data/instrument_validation.py'),protocol_sha256=ph)
        row.update({f'spectrum_{i:02d}':float(v) for i,v in enumerate(arrays['spectrum'])});row.update({f'error_{i:02d}':float(v) for i,v in enumerate(arrays['error'])})
        if row['net_count_rate']<=5:excluded.append({**r,'reason':'HEASOFT_NET_RATE_NOT_ABOVE_5','net_count_rate':row['net_count_rate']});continue
        rows.append(row)
    if pending:raise RuntimeError(f'{len(pending)} selected observations still lack terminal reduction/acquisition records; first {pending[:5]}')
    f=pd.DataFrame(rows);counts=f.groupby('source_id').size();small=set(counts[counts<2].index)
    for r in f[f.source_id.isin(small)].to_dict('records'):excluded.append({**r,'reason':'FEWER_THAN_TWO_USABLE_OBSERVATIONS_FOR_SOURCE'})
    f=f[~f.source_id.isin(small)].sort_values(['source_id','observation_time','rxte_obsid']).reset_index(drop=True)
    cohorts={'HEASOFT_VALIDATION':f[f.origin.eq('PRIMARY_29')].copy(),'EXPANDED_SOURCE':f.copy()}
    cohorts['HEASOFT_MATCHED']=common_support(cohorts['HEASOFT_VALIDATION'])
    frozen=ROOT/'results/validation_heasoft/dataset_freeze.json'
    if frozen.exists():raise ValueError('Validation data already frozen; cannot overwrite')
    paths={}
    for name,data in cohorts.items():
        p=validation_path(ROOT,'data/processed/validation_heasoft/'+name.lower()+'_observations.csv');data.to_csv(p,index=False);paths[str(p.relative_to(ROOT))]=sha256(p)
    pd.DataFrame(excluded).to_csv(validation_path(ROOT,'data/processed/validation_heasoft/excluded_observations.csv'),index=False)
    report=dict(protocol_sha256=ph,dataset_sha256=paths,cohorts={name:dict(observations=len(g),sources=g.source_id.nunique(),BH_sources=g[g.class_label.eq('BH')].source_id.nunique(),NS_sources=g[g.class_label.eq('NS')].source_id.nunique()) for name,g in cohorts.items()},selected=len(selections),excluded=len(excluded))
    frozen.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));verify_primary(ROOT)

if __name__=='__main__':main()
