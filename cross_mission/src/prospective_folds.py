"""Identity-only census demonstration, explicitly not an ML dataset freeze."""
import json
import pandas as pd
from evidence import ROOT, sha256
from contracts import make_folds

def main():
    rxte=pd.read_csv(ROOT.parent/'data/processed/validation_heasoft/expanded_source_observations.csv',dtype={'rxte_obsid':str})
    nu=pd.read_csv(ROOT/'data/manifests/nustar_inventory.csv',dtype={'obsid':str})
    nu=nu[nu.census_candidate]
    rxte=rxte.rename(columns={'rxte_obsid':'obsid','source_id':'physical_source'}).assign(mission='RXTE')
    nu=nu.rename(columns={'source_id':'physical_source'}).assign(mission='NuSTAR')
    columns=['mission','obsid','physical_source']
    rows=pd.concat([rxte[columns],nu[columns]],ignore_index=True)
    folds=make_folds(rows)
    rows.to_csv(ROOT/'data/manifests/prospective_identity_rows.csv',index=False)
    result=dict(status='PROSPECTIVE_CENSUS_CONTRACT_ONLY_NOT_X3_PASS',input_hash=sha256(ROOT/'data/manifests/prospective_identity_rows.csv'),labels_seen_by_allocator=False,folds=folds)
    (ROOT/'data/manifests/prospective_cross_mission_folds.json').write_text(json.dumps(result,indent=2)+'\n')
    audit=[]
    for f in folds:
        audit.append(dict(fold=f['fold_id'],training_sources=len(f['train_sources']),test_sources=len(f['test_sources']),training_observations=len(f['train_obsids']),test_observations=len(f['test_obsids']),physical_source_overlap=len(set(f['train_sources'])&set(f['test_sources'])),target_mission_training_observations=0))
    pd.DataFrame(audit).to_csv(ROOT/'results/prospective_leakage_audit.csv',index=False)
    print(pd.DataFrame(audit).to_string(index=False))

if __name__=='__main__':main()
