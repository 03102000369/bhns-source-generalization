"""Predeclared non-HEASoft controls on unchanged primary detector-space spectra."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from bhns.data.core_gate import load_core_frame
from bhns.data.instrument_validation import *
from bhns.experiments.instrument_validation import run_validation

ROOT=Path(__file__).resolve().parents[1]

def main():
    verify_primary(ROOT);validation_protocol(ROOT)
    original=load_core_frame(ROOT)
    meta=pd.read_csv(ROOT/'results/validation_heasoft/confounder_table.csv').rename(columns={'rxte_obsid':'obs_id'})
    frame=original.merge(meta[['obs_id']+META_FEATURES+['gain_epoch','background_fraction']],on='obs_id',validate='one_to_one')
    matched=pd.read_csv(ROOT/'data/processed/validation_heasoft/matched_observations.csv')
    runs=[];metadata_predictions=[];effects=[]
    def run(data,tag,model,mode,columns):
        p,s,a=run_validation(data,ROOT,tag,model,mode,columns);runs.append(s)
        if columns==META_FEATURES:
            p['model']=model;p['split']=mode;metadata_predictions.append(p)
        if columns==SPECTRAL_FEATURES:
            for au in a:
                for i,v in enumerate(au['feature_effect']):effects.append(dict(tag=tag,model=model,split=mode,fold=au['outer']['fold_id'],energy_keV=float((ENERGY_EDGES[i]+ENERGY_EDGES[i+1])/2),effect=v,effect_type=au['effect_type']))
    for model in ['logistic','forest']:
        run(frame,'metadata_'+model,model,'grouped',META_FEATURES)
        for mode in ['grouped','loso']:run(frame[frame.obs_id.isin(matched.rxte_obsid)],'matched_'+model+'_'+mode,model,mode,SPECTRAL_FEATURES)
        shape=frame.copy();shape[SPECTRAL_FEATURES]=shape_normalize(shape[SPECTRAL_FEATURES])
        run(shape,'shape_'+model,model,'grouped',SPECTRAL_FEATURES)
    for threshold in [.25,.5]:
        g=frame[frame.background_fraction.le(threshold)].copy();counts=g.groupby('source_id').size();g=g[g.source_id.isin(counts[counts>=2].index)]
        for model in ['logistic','forest']:run(g,f'background_{threshold}_{model}',model,'grouped',SPECTRAL_FEATURES)
    pd.concat(metadata_predictions).to_csv(validation_path(ROOT,'results/validation_heasoft/metadata_only_predictions.csv'),index=False)
    pd.DataFrame(effects).to_csv(validation_path(ROOT,'results/validation_heasoft/feature_effects.csv'),index=False)
    (ROOT/'results/validation_heasoft/diagnostic_metrics.json').write_text(json.dumps(runs,indent=2))
    epoch=[]
    for e in sorted(frame.gain_epoch.unique()):
        test=frame[frame.gain_epoch.eq(e)];n=test.groupby('source_id').size();test=test[test.source_id.isin(n[n>=2].index)]
        train=frame[~frame.gain_epoch.eq(e)&~frame.source_id.isin(test.source_id)]
        tc=test[['source_id','compact_object_class']].drop_duplicates().compact_object_class.value_counts();tr=train[['source_id','compact_object_class']].drop_duplicates().compact_object_class.value_counts()
        feasible=all(tc.get(c,0)>=2 and tr.get(c,0)>=5 for c in ['BH','NS'])
        epoch.append(dict(epoch=int(e),test_BH=int(tc.get('BH',0)),test_NS=int(tc.get('NS',0)),train_BH=int(tr.get('BH',0)),train_NS=int(tr.get('NS',0)),feasible=feasible,reason='Enough independent sources' if feasible else 'Fails predeclared >=2 test and >=5 training sources per class after source exclusion'))
        if feasible:raise NotImplementedError('Feasible epoch holdout requires explicit run; do not label complete')
    (ROOT/'results/validation_heasoft/epoch_holdout_feasibility.json').write_text(json.dumps(epoch,indent=2));verify_primary(ROOT)

if __name__=='__main__':main()
