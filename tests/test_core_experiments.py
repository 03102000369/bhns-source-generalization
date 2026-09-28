"""Software-only fixtures test isolation/statistics; never reported as astronomy."""
import numpy as np
import pandas as pd
import pytest

from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.bootstrap import bootstrap_sources
from bhns.evaluation.metrics import binary_metrics
from bhns.experiments.core import experiment,fit_and_predict,outer_folds
from bhns.experiments.source_permutation import permute_source_labels


def test_perfect_and_inverted_predictions_have_expected_metrics():
    y=[0,0,1,1];good=binary_metrics(y,[.1,.2,.8,.9]);bad=binary_metrics(y,[.9,.8,.2,.1])
    for k in ['AUROC','balanced_accuracy','MCC','F1','precision','recall','PR_AUC']:assert good[k]==1
    assert good['Brier']==pytest.approx(.025)
    assert bad['AUROC']==0 and bad['balanced_accuracy']==0 and bad['MCC']==-1


def test_prior_has_chance_balanced_accuracy():
    metrics=binary_metrics([0,0,1,1,1],[.6]*5)
    assert metrics['AUROC']==.5 and metrics['balanced_accuracy']==.5 and metrics['MCC']==0


def test_aggregation_does_not_weight_prolific_sources(observations):
    p=observations[['source_id','source_name','obs_id','compact_object_class']].rename(columns={'compact_object_class':'true_class'}).copy()
    p['p_NS']=.7
    sources=aggregate_sources(p)
    assert len(sources)==12
    assert sources.n_observations.sum()==len(p)
    np.testing.assert_allclose(sources.p_NS,.7)
    ci=bootstrap_sources(sources,sources,repetitions=20,seed=42)
    assert all(v['lower']==0 and v['upper']==0 for v in ci.values())
    with pytest.raises(ValueError,match='one row'):bootstrap_sources(pd.concat([sources,sources]),repetitions=2)


def test_bootstrap_requires_same_physical_sources(observations):
    p=observations[['source_id','source_name','obs_id','compact_object_class']].rename(columns={'compact_object_class':'true_class'}).copy();p['p_NS']=.6
    source=aggregate_sources(p);other=source.copy();other.loc[0,'source_id']='WRONG'
    with pytest.raises(ValueError,match='identical'):bootstrap_sources(source,other,repetitions=2)


@pytest.mark.parametrize('mode',['observation','grouped','loso'])
def test_outer_partitions_cover_each_observation_exactly_once(observations,mode):
    folds=outer_folds(observations,mode)
    assert sorted(i for f in folds for i in f.test)==list(range(len(observations)))
    if mode!='observation':
        for f in folds:assert set(observations.iloc[list(f.train)].source_id).isdisjoint(observations.iloc[list(f.test)].source_id)


def test_real_runner_tunes_only_inside_outer_training_and_refits_fresh(observations):
    outer=outer_folds(observations,'grouped')[0]
    pred,audit=fit_and_predict(observations,outer,'logistic')
    test=set(observations.iloc[list(outer.test)].obs_id)
    assert set(pred.obs_id)==test
    assert set(audit['final_fit_obs_ids'])==set(observations.iloc[list(outer.train)].obs_id)
    for partition in ['train','validation']:
        assert not test&set(audit['inner_fold'][partition]['obs_ids'])
        assert set(audit['inner_fold'][partition]['source_ids']).isdisjoint(audit['inner_fold']['test']['source_ids'])
    assert len(audit['selection_records'])==4
    assert len(audit['feature_columns'])==43


def test_error_representation_and_PCA_remain_training_bound(observations):
    outer=outer_folds(observations,'grouped',representation='SEM')[0]
    pred,audit=fit_and_predict(observations,outer,'logistic',representation='SEM',pca=5,fixed_parameters={'C':1.})
    assert len(audit['feature_columns'])==86
    assert audit['inner_fold'] is None
    assert set(pred.obs_id).isdisjoint(audit['final_fit_obs_ids'])


def test_group_stratification_remains_feasible_under_source_randomization(observations):
    for seed in range(100,150):
        labels,_=permute_source_labels(observations,seed=seed)
        f=observations.copy();f['compact_object_class']=labels.map({0:'BH',1:'NS'})
        folds=outer_folds(f,'grouped')
        for fold in folds:assert f.iloc[list(fold.test)].compact_object_class.nunique()==2
