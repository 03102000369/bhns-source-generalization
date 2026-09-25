"""Freeze after real-data gates pass, then run the bounded primary and diagnostic studies."""
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

from bhns.config import config_hash
from bhns.data.core_gate import load_core_frame,validate_core
from bhns.data.preprocessing import TrainingOnlyPreprocessor
from bhns.data.rxte_products import sha256
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.bootstrap import bootstrap_sources
from bhns.evaluation.metrics import binary_metrics
from bhns.evaluation.splits import make_fold
from bhns.experiments.core import experiment,fit_and_predict,outer_folds
from bhns.experiments.source_permutation import permute_source_labels
from bhns.reproducibility import write_json

ROOT=Path(__file__).resolve().parents[1]


def freeze_protocol(frame):
    gate=validate_core(ROOT)
    if gate['status']!='PASS':raise RuntimeError('Gate 1A must pass: '+str(gate['problems']))
    review=json.loads((ROOT/'reports/gates_0_2_real_data_review.json').read_text())
    foundation=json.loads((ROOT/'reports/foundation_check.json').read_text())
    data_sha=sha256(ROOT/'data/processed/observations.csv')
    if review['status']!='PASS' or review.get('dataset_sha256')!=data_sha or foundation['tests']['exit_code']!=0:
        raise RuntimeError('Run check_foundation.py successfully on this exact dataset before freezing')
    path=ROOT/'configs/experiment_protocol_frozen.yaml'
    if path.exists():
        p=yaml.safe_load(path.read_text())
        if p['dataset_sha256']!=data_sha:raise RuntimeError('Dataset changed after protocol freeze')
        if (ROOT/'configs/experiment_protocol_frozen.sha256').read_text().strip()!=config_hash(p):raise RuntimeError('Frozen protocol hash changed')
        return p
    p=dict(seed=42,experiment=dict(name='core-source-generalization',model='prior_logistic_forest',scientific_runs_enabled=True),
           frozen_at=datetime.now(timezone.utc).isoformat(),dataset_sha256=data_sha,
           reconstruction_config_sha256=sha256(ROOT/'configs/reconstruction.yaml'),
           class_mapping=dict(BH=0,NS=1),positive_class='NS',
           source_cohort=frame[['source_id','source_name','compact_object_class']].drop_duplicates().to_dict('records'),
           source_exclusions_file='data/reference/reference_source_roster.csv',source_exclusions_sha256=sha256(ROOT/'data/reference/reference_source_roster.csv'),
           features=dict(primary='43 recorded 5–25 keV detector-space rates',secondary='same 43 rates + 43 archive statistical errors on identical cohort',PM='optional unavailable'),
           primary_models=['prior','logistic','forest'],prior_definition='fixed uninformed p_NS=0.5; threshold tie assigned NS; avoids pooling fold-dependent empirical priors',
           preprocessing=dict(standardize=True,imputation=None,PCA=None,feature_selection=None),
           source_weighting='equal_source_training_total_weight',outer_splits=['5-fold stratified observation OOF','5-fold stratified physical-source OOF','LOSO'],
           inner_split='20 percent stratified physical-source validation from outer training only',
           model_selection=dict(metric='source_balanced_accuracy',tie_break='first candidate',refit='fresh preprocessing and chosen model on complete outer training',
                                logistic_C=[.01,.1,1.,10.],forest_max_depth=[4,None],forest_trees=100,forest_min_samples_leaf=3),
           primary_metric='source-level AUROC',other_metrics=['balanced_accuracy','MCC','F1','precision','recall','PR_AUC_average_precision','Brier','accuracy'],
           aggregation='mean log-odds; clip probabilities to [1e-7,1-1e-7]',threshold=.5,
           uncertainty=dict(unit='physical_source',method='class-stratified percentile bootstrap',repetitions=2000,level=.95,
                            qualification='conditional on selected cohort; training not rerun inside bootstrap'),
           primary_comparison='paired observation OOF minus grouped OOF metric on the identical sources and observations; source-overlap-associated inflation',
           randomization=dict(seeds=list(range(100,150)),unit='physical_source',model='forest',parameters=dict(max_depth=None),
                              folds='regenerated with fixed seed 42 stratifying randomized source labels; observation and grouped designs',tuning='none; fixed diagnostic model'),
           learning_curve=dict(seeds=list(range(200,205)),model='logistic',C=1.,training_sources_per_class=[2,3,5],outer='fixed primary grouped test sources',
                               tuning='none; fixed diagnostic model; equal numbers of BH/NS training sources'),
           robustness=['observation-weighted training','PCA 95 percent variance','spectra+errors identical cohort','remove most observed source (lexical tie break)',
                       'remove observations above 1000 count/s/PCU and sources left with fewer than four observations','grouped split seeds 43 and 44',
                       'fixed logistic C=0.01 and C=10'],
           source_identification='exploratory 3-fold observation-stratified-by-source random forest, 100 trees',
           limits=['No claim of exact reference replication','Detector response/epoch and deadtime remain possible confounders',
                   'Archive formal errors exclude background and calibration systematics','No provisional sources enter the primary cohort'])
    with path.open('x') as h:yaml.safe_dump(p,h,sort_keys=True)
    (ROOT/'configs/experiment_protocol_frozen.sha256').write_text(config_hash(p)+'\n')
    return p


def summarize(sources,model,mode,tag,bootstrap=True):
    metrics=binary_metrics(sources.true_class.eq('NS'),sources.p_NS)
    interval=bootstrap_sources(sources,repetitions=2000,seed=42) if bootstrap else {}
    result=dict(model=model,split=mode,analysis=tag,unit='physical_source',sources=len(sources),observations=int(sources.n_observations.sum()))|metrics
    for k,v in interval.items():result[k+'_lower']=v['lower'];result[k+'_upper']=v['upper']
    return result


def main():
    frame=load_core_frame(ROOT);protocol=freeze_protocol(frame)
    results=ROOT/'results';primary=[];all_sources={};all_predictions=[]
    for model in protocol['primary_models']:
        for mode in ['observation','grouped','loso']:
            tag=f'primary_{model}_{mode}';print(tag,flush=True)
            pred,sources,audits=experiment(frame,ROOT,protocol,model=model,mode=mode,tag=tag)
            if mode=='loso':
                distances=pd.DataFrame([a['heldout_spectral_distance'] for a in audits])
                sources=sources.merge(distances,on='source_id',validate='one_to_one')
            pred['model']=model;pred['split']=mode;all_predictions.append(pred)
            sources['model']=model;sources['split']=mode;all_sources[(model,mode)]=sources
            primary.append(summarize(sources,model,mode,'primary'))
            pd.DataFrame(primary).to_csv(results/'primary_performance.csv',index=False)
    predictions=pd.concat(all_predictions,ignore_index=True);predictions.to_csv(results/'primary_predictions.csv',index=False)
    predictions[predictions.split.eq('loso')].to_csv(results/'loso_predictions.csv',index=False)
    pd.concat([v for (m,s),v in all_sources.items() if s=='loso']).to_csv(results/'loso_source_summary.csv',index=False)
    differences=[]
    for model in protocol['primary_models']:
        a=all_sources[(model,'observation')];b=all_sources[(model,'grouped')]
        interval=bootstrap_sources(a,b,repetitions=2000,seed=42)
        ma=binary_metrics(a.true_class.eq('NS'),a.p_NS);mb=binary_metrics(b.true_class.eq('NS'),b.p_NS)
        for metric in ma:differences.append(dict(model=model,metric=metric,delta=ma[metric]-mb[metric],**interval[metric]))
    pd.DataFrame(differences).to_csv(results/'paired_performance_difference.csv',index=False)
    pd.DataFrame([dict(model=model,split=mode,unit='observation_descriptive_only',**binary_metrics(g.true_class.eq('NS'),g.p_NS))
                  for (model,mode),g in predictions.groupby(['model','split'])]).to_csv(results/'observation_metrics_secondary.csv',index=False)
    controls=[];control_predictions=[]
    for seed in protocol['randomization']['seeds']:
        labels,mapping=permute_source_labels(frame,seed=seed)
        randomized=frame.copy();randomized['astrophysical_class']=frame.compact_object_class
        randomized['compact_object_class']=labels.map({0:'BH',1:'NS'})
        for mode in ['observation','grouped']:
            pred,sources,_=experiment(randomized,ROOT,protocol,model='forest',mode=mode,tag=f'null_{seed}_{mode}',fixed_parameters=dict(max_depth=None))
            controls.append(dict(permutation_seed=seed,model='forest',split=mode,**binary_metrics(sources.true_class.eq('NS'),sources.p_NS)))
            pred['permutation_seed']=seed;pred['split']=mode;control_predictions.append(pred)
        pd.DataFrame(controls).to_csv(results/'source_randomization_results.csv',index=False)
        print('Source permutation',seed,flush=True)
    pd.concat(control_predictions).to_csv(results/'source_randomization_predictions.csv',index=False)
    robust=[]
    variants=[('observation_weights',frame,dict(weighting='observation')),
              ('PCA_95pct',frame,dict(pca=.95)),('SEM_same_cohort',frame,dict(representation='SEM'))]
    sizes=frame.groupby('source_id').size();heavy=sorted(sizes[sizes==sizes.max()].index)[0]
    variants.append(('drop_most_observed_'+heavy,frame[frame.source_id.ne(heavy)].reset_index(drop=True),{}))
    faint=frame[frame.net_count_rate.le(1000)].copy();keep=faint.groupby('source_id').size();faint=faint[faint.source_id.isin(keep[keep>=4].index)].reset_index(drop=True)
    variants.append(('exclude_above_1000_count_s_PCU',faint,{}))
    variants += [(f'grouped_seed_{s}',frame,dict(seed=s)) for s in [43,44]]
    variants += [(f'fixed_C_{c}',frame,dict(fixed_parameters=dict(C=c))) for c in [.01,10.]]
    for tag,subset,options in variants:
        print('Sensitivity',tag,flush=True)
        pred,sources,_=experiment(subset,ROOT,protocol,model='logistic',mode='grouped',tag='sensitivity_'+tag,**options)
        robust.append(summarize(sources,'logistic','grouped',tag))
        pd.DataFrame(robust).to_csv(results/'robustness_results.csv',index=False)
    curve=[]
    for outer in outer_folds(frame,'grouped'):
        pool=frame.iloc[list(outer.train)][['source_id','compact_object_class']].drop_duplicates()
        for seed in protocol['learning_curve']['seeds']:
            for size in protocol['learning_curve']['training_sources_per_class']:
                if pool.groupby('compact_object_class').size().min()<size:continue
                rng=np.random.default_rng(seed)
                chosen=set(np.concatenate([rng.choice(pool[pool.compact_object_class.eq(c)].source_id,size,replace=False) for c in ['BH','NS']]))
                test_sources=set(frame.iloc[list(outer.test)].source_id)
                subset=frame[frame.source_id.isin(chosen|test_sources)].reset_index(drop=True)
                mask=subset.source_id.isin(test_sources).to_numpy()
                fold=make_fold(subset,np.flatnonzero(~mask),np.flatnonzero(mask),mode='grouped',seed=seed,fold_id=outer.fold_id,representation='SM')
                pred,_=fit_and_predict(subset,fold,'logistic',seed=seed,fixed_parameters=dict(C=1.))
                source=aggregate_sources(pred)
                curve.append(dict(seed=seed,fold=outer.fold_id,training_sources=2*size,training_sources_per_class=size,test_sources=len(source),
                                  training_source_ids='|'.join(sorted(chosen)),**binary_metrics(source.true_class.eq('NS'),source.p_NS)))
    pd.DataFrame(curve).to_csv(results/'source_learning_curve.csv',index=False)
    identity=[]
    splitter=StratifiedKFold(3,shuffle=True,random_state=42)
    for n,(train,test) in enumerate(splitter.split(np.zeros(len(frame)),frame.source_id)):
        fold=make_fold(frame,train,test,mode='observation',seed=42,fold_id=f'identity-{n}',representation='SM')
        prep=TrainingOnlyPreprocessor('SM').fit(frame,fold)
        model=RandomForestClassifier(n_estimators=100,min_samples_leaf=2,random_state=42,n_jobs=2)
        model.fit(prep.transform(frame,partition='train'),frame.iloc[train].source_id)
        pred=model.predict(prep.transform(frame,partition='test'))
        for index,value in zip(test,pred):identity.append(dict(obs_id=frame.iloc[index].obs_id,source_id=frame.iloc[index].source_id,predicted_source_id=value,correct=value==frame.iloc[index].source_id))
    pd.DataFrame(identity).to_csv(results/'source_identification_predictions.csv',index=False)
    write_json(results/'experiment_completion.json',dict(completed_at=datetime.now(timezone.utc).isoformat(),protocol_hash=config_hash(protocol),
               dataset_sha256=protocol['dataset_sha256'],primary_models=protocol['primary_models'],permutations=50,
               sources=frame.source_id.nunique(),observations=len(frame),status='COMPLETED',
               output_sha256={str(p.relative_to(ROOT)):sha256(p) for p in sorted(results.glob('*.csv'))}))
    print('All primary and diagnostic experiments completed',flush=True)


if __name__=='__main__':main()
