"""Critical grouped/LOSO transfer and smaller fingerprint control, isolated outputs."""
from pathlib import Path
import json
import pandas as pd
from bhns.data.instrument_validation import *
from bhns.data.core_gate import load_core_frame
from bhns.experiments.instrument_validation import run_validation,fit_fold
from bhns.evaluation.splits import Fold,dataset_fingerprint
from bhns.evaluation.metrics import binary_metrics
from bhns.experiments.source_permutation import permute_source_labels
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.bootstrap import bootstrap_sources
ROOT=Path(__file__).resolve().parents[1]

def adapt(f):
    out=f[['source_id','canonical_source','class_label','rxte_obsid','net_count_rate','observation_time']].rename(columns={'canonical_source':'source_name','class_label':'compact_object_class','rxte_obsid':'obs_id'}).copy()
    for i in range(43):out[f'flux_{i:02d}']=f[f'spectrum_{i:02d}'].to_numpy()
    return out.reset_index(drop=True)

def main():
    verify_primary(ROOT);validation_protocol(ROOT);lock=json.loads((ROOT/'results/validation_heasoft/dataset_freeze.json').read_text())
    for p,h in lock['dataset_sha256'].items():
        if sha256(ROOT/p)!=h:raise ValueError('Frozen validation dataset changed')
    ad=ROOT/'configs/validation_heasoft_comparison_addendum.yaml'
    if sha256(ad)!=ad.with_suffix('.sha256').read_text().strip():raise ValueError('Comparison addendum changed')
    cohorts={name:adapt(pd.read_csv(ROOT/f'data/processed/validation_heasoft/{name.lower()}_observations.csv')) for name in ['HEASOFT_VALIDATION','HEASOFT_MATCHED','EXPANDED_SOURCE']}
    primary=load_core_frame(ROOT)
    # Match row order too: a fixed forest seed must resample identical ObsIDs,
    # rather than different positional rows in an otherwise identical cohort.
    cohorts['PRIMARY_SAME_OBSIDS']=primary.set_index('obs_id').loc[cohorts['HEASOFT_VALIDATION'].obs_id].reset_index()
    if not cohorts['PRIMARY_SAME_OBSIDS'].obs_id.equals(cohorts['HEASOFT_VALIDATION'].obs_id):raise ValueError('Comparator row order differs')
    # The frozen shape/background sensitivities also apply to the independent
    # reduction, not only the already completed primary-data diagnostics.
    shape=cohorts['HEASOFT_VALIDATION'].copy()
    shape[SPECTRAL_FEATURES]=shape_normalize(shape[SPECTRAL_FEATURES])
    cohorts['HEASOFT_SHAPE']=shape
    physical=pd.read_csv(ROOT/'data/processed/validation_heasoft/heasoft_validation_observations.csv')
    for threshold in [.25,.5]:
        selected=physical[physical.background_fraction.le(threshold)].copy()
        counts=selected.groupby('source_id').size()
        selected=selected[selected.source_id.isin(counts[counts>=2].index)]
        cohorts[f'HEASOFT_BACKGROUND_{threshold}']=adapt(selected)
    summaries=[];preds={};skipped=[];effects=[]
    for name,frame in cohorts.items():
        counts=frame[['source_id','compact_object_class']].drop_duplicates().compact_object_class.value_counts()
        if any(counts.get(c,0)<5 for c in ['BH','NS']):skipped.append(dict(cohort=name,reason='Predeclared minimum five sources per class not met',counts=counts.to_dict()));continue
        for model in ['logistic','forest']:
            for split in (['grouped'] if name=='HEASOFT_SHAPE' or name.startswith('HEASOFT_BACKGROUND_') else ['grouped','loso']):
                p,s,a=run_validation(frame,ROOT,name+'_'+model+'_'+split,model,split,SPECTRAL_FEATURES);s['cohort']=name;summaries.append(s);preds[(name,model,split)]=p
                for audit in a:
                    for i,v in enumerate(audit['feature_effect']):effects.append(dict(cohort=name,model=model,split=split,fold=audit['outer']['fold_id'],energy_keV=float((ENERGY_EDGES[i]+ENERGY_EDGES[i+1])/2),effect=v,effect_type=audit['effect_type']))
    control=[];frame=cohorts['HEASOFT_VALIDATION']
    if any(x['cohort']=='HEASOFT_VALIDATION' for x in summaries):
        for seed in range(300,310):
            labels,_=permute_source_labels(frame,seed=seed);g=frame.copy();g['compact_object_class']=labels.map({0:'BH',1:'NS'})
            for mode in ['observation','grouped']:
                _,s,_=run_validation(g,ROOT,f'HEASOFT_randomized_{seed}_{mode}','forest',mode,SPECTRAL_FEATURES,fixed={'max_depth':None},bootstrap=False);control.append(dict(seed=seed,split=mode,**s['metrics']))
    pd.DataFrame(control).to_csv(validation_path(ROOT,'results/validation_heasoft/source_randomization_results.csv'),index=False)
    pd.DataFrame(effects).to_csv(validation_path(ROOT,'results/validation_heasoft/heasoft_feature_effects.csv'),index=False)
    paired=[]
    for model in ['logistic','forest']:
        for split in ['grouped','loso']:
            a=preds.get(('HEASOFT_VALIDATION',model,split));b=preds.get(('PRIMARY_SAME_OBSIDS',model,split))
            if a is not None and b is not None:paired.append(dict(model=model,split=split,definition='HEASOFT minus original rates on identical admitted ObsIDs',intervals=bootstrap_sources(aggregate_sources(a),aggregate_sources(b))))
    (ROOT/'results/validation_heasoft/heasoft_model_metrics.json').write_text(json.dumps(dict(completed=summaries,skipped=skipped,paired=paired),indent=2));verify_primary(ROOT)
    epochs=[]
    for epoch in sorted(physical.gain_epoch.unique()):
        test=physical[physical.gain_epoch.eq(epoch)].copy();counts=test.groupby('source_id').size();test=test[test.source_id.isin(counts[counts>=2].index)]
        train=physical[~physical.gain_epoch.eq(epoch)&~physical.source_id.isin(test.source_id)].copy()
        tc=test[['source_id','class_label']].drop_duplicates().class_label.value_counts();tr=train[['source_id','class_label']].drop_duplicates().class_label.value_counts()
        feasible=all(tc.get(c,0)>=2 and tr.get(c,0)>=5 for c in ['BH','NS'])
        rec=dict(epoch=int(epoch),test_BH=int(tc.get('BH',0)),test_NS=int(tc.get('NS',0)),train_BH=int(tr.get('BH',0)),train_NS=int(tr.get('NS',0)),feasible=feasible,models=[])
        if feasible:
            joint=adapt(pd.concat([train,test],ignore_index=True));fold=Fold(tuple(range(len(train))),tuple(range(len(train),len(joint))),'grouped',42,f'epoch-{epoch}',dataset_fingerprint(joint),representation='SM')
            for model in ['logistic','forest']:
                pred,audit=fit_fold(joint,fold,model,SPECTRAL_FEATURES);source=aggregate_sources(pred)
                rec['models'].append(dict(model=model,metrics=binary_metrics(source.true_class.eq('NS'),source.p_NS),intervals=bootstrap_sources(source),audit=audit))
                pred.to_csv(validation_path(ROOT,f'results/validation_heasoft/epoch_{epoch}_{model}_predictions.csv'),index=False)
        else:rec['reason']='Fails predeclared >=2 test and >=5 training sources per class after excluding all test identities'
        epochs.append(rec)
    validation_path(ROOT,'results/validation_heasoft/heasoft_epoch_holdout_results.json').write_text(json.dumps(epochs,indent=2))

if __name__=='__main__':main()
