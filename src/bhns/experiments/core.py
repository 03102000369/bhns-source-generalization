"""Modest source-aware experiments using the existing fold/preprocessing contracts."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import NearestNeighbors

from bhns.config import config_hash
from bhns.data.preprocessing import TrainingOnlyPreprocessor
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.grouped_cv import grouped_folds
from bhns.evaluation.loso import loso_folds
from bhns.evaluation.metrics import binary_metrics
from bhns.evaluation.splits import add_inner_validation,fold_definition,make_fold,validate_fold
from bhns.experiments.source_balancing import source_weights
from bhns.reproducibility import run_record,save_predictions


def outer_folds(frame,mode,seed=42,representation='SM'):
    if mode=='grouped':return grouped_folds(frame,n_splits=5,seed=seed,representation=representation)
    if mode=='loso':return loso_folds(frame,seed=seed,representation=representation)
    if mode!='observation':raise ValueError('Unknown evaluation mode')
    splitter=StratifiedKFold(5,shuffle=True,random_state=seed)
    return [make_fold(frame,a,b,mode='observation',seed=seed,fold_id=f'observation-{n:02d}',representation=representation)
            for n,(a,b) in enumerate(splitter.split(np.zeros(len(frame)),frame.compact_object_class))]


def estimator(name,parameters,seed):
    if name=='prior':return DummyClassifier(strategy='uniform',random_state=seed)
    if name=='logistic':return LogisticRegression(solver='liblinear',max_iter=3000,random_state=seed,**parameters)
    if name=='forest':return RandomForestClassifier(n_estimators=100,min_samples_leaf=3,n_jobs=2,random_state=seed,**parameters)
    raise ValueError('Unknown model')


def candidate_parameters(name):
    return {'prior':[{}],'logistic':[dict(C=c) for c in [.01,.1,1.,10.]],'forest':[dict(max_depth=d) for d in [4,None]]}[name]


def _prediction(frame,positions,p):
    result=frame.iloc[list(positions)][['source_id','source_name','obs_id','compact_object_class']].copy().rename(columns={'compact_object_class':'true_class'})
    result['p_NS']=p;result['p_BH']=1-p
    return result


def fit_and_predict(frame,outer,model,*,seed=42,representation='SM',weighting='equal_source',pca=None,fixed_parameters=None):
    """Tune inside outer training, then fresh refit on all outer-training rows."""
    validate_fold(frame,outer)
    y=frame.compact_object_class.eq('NS').astype(int).to_numpy()
    candidates=candidate_parameters(model) if fixed_parameters is None else [fixed_parameters]
    tuning=[];inner=None
    if len(candidates)>1:
        inner=add_inner_validation(frame,outer,validation_fraction=.2,seed=seed)
        prep=TrainingOnlyPreprocessor(representation,standardize=True,pca_components=pca,seed=seed).fit(frame,inner)
        xtrain=prep.transform(frame,partition='train');xval=prep.transform(frame,partition='validation')
        weights=source_weights(frame.iloc[list(inner.train)]) if weighting=='equal_source' else None
        for parameters in candidates:
            clf=estimator(model,parameters,seed);clf.fit(xtrain,y[list(inner.train)],sample_weight=weights)
            p=clf.predict_proba(xval)[:,1]
            sources=aggregate_sources(_prediction(frame,inner.validation,p))
            score=binary_metrics(sources.true_class.eq('NS'),sources.p_NS)['balanced_accuracy']
            tuning.append(dict(parameters=parameters,source_balanced_accuracy=score))
        best=max(range(len(tuning)),key=lambda i:tuning[i]['source_balanced_accuracy'])
        parameters=candidates[best]
    else:parameters=candidates[0]
    prep=TrainingOnlyPreprocessor(representation,standardize=True,pca_components=pca,seed=seed).fit(frame,outer)
    if set(prep.fit_obs_ids_) & set(frame.iloc[list(outer.test)].obs_id):raise ValueError('Test observations entered final fitting')
    weights=source_weights(frame.iloc[list(outer.train)]) if weighting=='equal_source' else None
    clf=estimator(model,parameters,seed)
    xtrain=prep.transform(frame,partition='train');xtest=prep.transform(frame,partition='test')
    clf.fit(xtrain,y[list(outer.train)],sample_weight=weights)
    p=clf.predict_proba(xtest)[:,1]
    distance=None
    if outer.mode=='loso':
        distances=NearestNeighbors(n_neighbors=1).fit(xtrain).kneighbors(xtest)[0][:,0]
        distance=dict(source_id=frame.iloc[list(outer.test)].source_id.iloc[0],median_nearest_training_spectral_distance=float(np.median(distances)))
    return _prediction(frame,outer.test,p),dict(selected_parameters=parameters,selection_records=tuning,heldout_spectral_distance=distance,
           inner_fold=None if inner is None else fold_definition(frame,inner),final_fit_obs_ids=list(prep.fit_obs_ids_),
           final_fit_source_ids=list(prep.fit_source_ids_),feature_columns=list(prep.columns),weighting=weighting,
           preprocessing=dict(standardize=True,pca_components=pca),early_stopping='not_used',feature_selection='not_used')


def experiment(frame,root,protocol,*,model,mode,tag,seed=42,representation='SM',weighting='equal_source',pca=None,fixed_parameters=None,save=True):
    root=Path(root);folds=outer_folds(frame,mode,seed,representation);pieces=[];audits=[]
    path=root/'results/runs'/tag
    for fold in folds:
        destination=path/f'{fold.fold_id}.csv'
        if save and destination.exists():
            stored=json.loads(destination.with_suffix('.json').read_text())
            if stored['configuration_hash']!=config_hash(protocol) or fold_definition(frame,fold) not in stored['split_definition']:
                raise ValueError('Existing prediction artifact belongs to a different frozen protocol or dataset')
            pred=pd.read_csv(destination);audit=stored['fit_audit']
        else:
            pred,audit=fit_and_predict(frame,fold,model,seed=seed,representation=representation,weighting=weighting,pca=pca,fixed_parameters=fixed_parameters)
            if save:
                metadata=run_record(protocol,project_root=root,frame=frame,folds=[fold],experiment_name=tag)
                metadata.update(record_kind='real_observation_predictions',model_type=model,fit_audit=audit,
                                metrics={'status':'held_out_predictions_metrics_computed_after_all_folds'})
                save_predictions(pred,destination,frame=frame,fold=fold,metadata=metadata)
        pieces.append(pred);audits.append(audit)
    predictions=pd.concat(pieces,ignore_index=True)
    if set(predictions.obs_id)!=set(frame.obs_id) or predictions.obs_id.duplicated().any():raise ValueError('Outer folds do not provide exactly one prediction per observation')
    sources=aggregate_sources(predictions)
    return predictions,sources,audits
