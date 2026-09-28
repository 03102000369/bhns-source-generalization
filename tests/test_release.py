"""Scientific release contracts using real frozen summaries; no new fitting."""
from pathlib import Path
import sys,json,csv
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_release import verify,scientific_contracts
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.metrics import binary_metrics

def test_all_packaged_hashes():assert verify()>100

def test_frozen_primary_cohort():assert scientific_contracts()['observations']==687

@pytest.mark.parametrize('mode,number',[('observation',5),('grouped',5),('loso',29)])
def test_actual_frozen_fold_membership(mode,number):
    obs=pd.read_csv(ROOT/'data/processed/observations.csv');obs=obs[obs.usable]
    identity=obs.set_index('rxte_obsid').source_id.to_dict()
    rec=json.loads((ROOT/'data/manifests/primary_split_definitions.json').read_text())
    folds=[r['outer'] for r in rec['folds'] if r['split']==mode]
    assert len(folds)==number
    assert sorted(o for f in folds for o in f['test']['obs_ids'])==sorted(identity)
    for f in folds:
        train=set(f['train']['obs_ids']);test=set(f['test']['obs_ids'])
        assert not train&test and train|test==set(identity)
        if mode!='observation':assert {identity[o] for o in train}.isdisjoint(identity[o] for o in test)

@pytest.mark.parametrize('model',['logistic','forest'])
@pytest.mark.parametrize('split',['observation','grouped','loso'])
def test_primary_scores_reproduce_frozen_point_metrics(model,split):
    pred=pd.read_csv(ROOT/('results/loso_predictions.csv' if split=='loso' else 'results/primary_predictions.csv'))
    pred=pred[pred.model.eq(model)]
    if 'split' in pred:pred=pred[pred.split.eq(split)]
    src=aggregate_sources(pred)
    actual=binary_metrics(src.true_class.eq('NS').astype(int),src.p_NS)
    frozen=pd.read_csv(ROOT/'results/primary_performance.csv')
    row=frozen[frozen.model.eq(model)&frozen.split.eq(split)].iloc[0]
    for metric in ['AUROC','balanced_accuracy','MCC','Brier']:
        assert actual[metric]==pytest.approx(row[metric],abs=1e-12)

def test_randomization_keeps_all_registered_permutations():
    a=pd.read_csv(ROOT/'results/source_randomization_results.csv')
    b=pd.read_csv(ROOT/'results/validation_heasoft/source_randomization_results.csv')
    assert a.groupby('split').size().to_dict()=={'grouped':50,'observation':50}
    assert b.groupby('split').size().to_dict()=={'grouped':10,'observation':10}

def test_confirmatory_state_gate_remains_infeasible():
    state=json.loads((ROOT/'results/state_extension/stage_status.json').read_text())
    assert state['ml_runs']==0 and not state['cohort_created']
    assert all(not r['PASS'] for r in state['regimes'])

def test_download_plan_contains_checksums_without_fetching():
    from download_recorded_products import planned
    items=planned();assert len(items)>1000
    assert all(len(r['sha256'])==64 and not p.is_absolute() for r,p in items)

def test_phase2_never_claims_a_completed_classifier():
    text=(ROOT/'docs/phase2_status.md').read_text()
    assert 'NOT YET TESTED' in text and 'NOT PASSED' in text and 'NOT RUN' in text
