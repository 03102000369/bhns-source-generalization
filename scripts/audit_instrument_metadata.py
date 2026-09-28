"""Rebuild isolated detector/epoch/GTI audits without modifying primary science."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from bhns.data.instrument_validation import *
ROOT=Path(__file__).resolve().parents[1]

def main():
    verify_primary(ROOT);validation_protocol(ROOT)
    f=primary_confounders(ROOT)
    for name in ['confounder_table','pcu_configuration']:f.to_csv(validation_path(ROOT,f'results/validation_heasoft/{name}.csv'),index=False)
    f.groupby(['gain_epoch','class_label']).agg(observations=('rxte_obsid','size'),sources=('source_id','nunique')).reset_index().to_csv(validation_path(ROOT,'results/validation_heasoft/gain_epoch_distribution.csv'),index=False)
    matched=common_support(f);data=pd.read_csv(ROOT/'data/processed/observations.csv');data=data[data.rxte_obsid.isin(matched.rxte_obsid)].merge(matched[['rxte_obsid','gain_epoch','selected_pcus','background_fraction']],on='rxte_obsid',validate='one_to_one')
    data.to_csv(validation_path(ROOT,'data/processed/validation_heasoft/matched_observations.csv'),index=False)
    rng=np.random.default_rng(42);features=['observation_year','exposure','num_selected_pcus','net_count_rate','background_fraction']
    s=f.groupby(['source_id','class_label'])[features].median().reset_index();s['epoch5_fraction']=f.assign(e5=f.gain_epoch.eq(5).astype(float)).groupby('source_id').e5.mean().reindex(s.source_id).to_numpy();features+=['epoch5_fraction'];labels=s.class_label.eq('BH').to_numpy();rows=[]
    for col in features:
        x=s[col].to_numpy();delta=np.mean(x[labels])-np.mean(x[~labels]);null=[]
        for _ in range(5000):
            p=rng.permutation(labels);null.append(np.mean(x[p])-np.mean(x[~p]))
        rows.append(dict(variable=col,BH_source_median=float(np.median(x[labels])),NS_source_median=float(np.median(x[~labels])),BH_minus_NS_source_mean=float(delta),source_label_permutation_p=(1+np.sum(np.abs(null)>=abs(delta)))/5001,unit='source median; within-source fraction for epoch5',interpretation='exploratory association; unadjusted multiple comparisons; not causal'))
    pd.DataFrame(rows).to_csv(validation_path(ROOT,'results/validation_heasoft/source_level_confounder_associations.csv'),index=False)
    print('Audit complete:',len(f),'observations;',len(matched),'matched; primary protected',verify_primary(ROOT))

if __name__=='__main__':main()
