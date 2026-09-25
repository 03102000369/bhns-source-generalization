"""Read-only verification of old artifacts, new preregistration, and fit partitions."""
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from bhns.data.state_validation import verify_protected,sha256,PROXY_FEATURES
from run_state_validation import load_proxy_frame
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'results/state_validation'
    counts={}
    for name in ['protected_artifact_manifest','frozen_manifest']:
        counts[name]=verify_protected(ROOT,json.loads((out/(name+'.json')).read_text()))
    product_hashes={}
    for name in ['heasoft_validation','heasoft_matched','expanded_source']:
        f=pd.read_csv(ROOT/f'data/processed/validation_heasoft/{name}_observations.csv')
        for row in f.itertuples():
            for kind in ['native','provenance']:
                p=getattr(row,kind+'_path');h=getattr(row,kind+'_sha256')
                if p in product_hashes and product_hashes[p]!=h:raise ValueError('Conflicting recorded product hashes')
                product_hashes[p]=h
    counts['recorded_native_and_provenance_products']=verify_protected(ROOT,product_hashes)
    (out/'recorded_product_manifest.json').write_text(json.dumps(product_hashes,indent=2))
    f=load_proxy_frame(ROOT);x=f[PROXY_FEATURES].to_numpy();protocol=json.loads((ROOT/'configs/state_validation_protocol_frozen.yaml').read_text());nfold=0
    summaries=[]
    for folder in sorted((out/'runs').glob('PROXY_ONLY_*')):
        s=json.loads((folder/'summary.json').read_text());assert s['protocol_sha256']==sha256(ROOT/'configs/state_validation_protocol_frozen.yaml');assert s['started_utc']>protocol['frozen_utc']
        for audit in json.loads((folder/'fit_audits.json').read_text()):
            a=audit['outer'];b=audit['inner'];assert audit['feature_columns']==PROXY_FEATURES
            for fold in [a,b]:
                train=set(fold['train']['source_ids']);val=set(fold['validation']['source_ids']);test=set(fold['test']['source_ids'])
                assert not (train&test or train&val or val&test)
            np.testing.assert_allclose(audit['scaler_mean'],x[a['train']['positions']].mean(0),rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(audit['inner_scaler_mean'],x[b['train']['positions']].mean(0),rtol=1e-12,atol=1e-12)
            assert set(audit['fit_obs_ids'])==set(a['train']['obs_ids']);assert set(audit['fit_source_ids'])==set(a['train']['source_ids']);nfold+=1
        summaries.append(dict(run=folder.name,started_utc=s['started_utc'],completed_utc=s['completed_utc']))
    for name in ['manuscript_results_report.md','novelty_positioning.md']:
        before=(ROOT/'reports/state_validation/snapshots'/name).read_bytes();now=(ROOT/'reports'/name).read_bytes();assert now.startswith(before)
    result=dict(checked_utc=datetime.now(timezone.utc).isoformat(),counts=counts,source_disjoint_fold_audits=nfold,protocol_sha256=sha256(ROOT/'configs/state_validation_protocol_frozen.yaml'),mismatches=[],existing_report_prefixes_preserved=True,runs=summaries)
    (out/'integrity_after.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
