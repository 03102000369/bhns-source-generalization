"""Artificial fixtures verify mechanics only, never astrophysical observations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from astropy.io import fits
from bhns.data.instrument_validation import *
from bhns.experiments.instrument_validation import matrix,fit_fold,run_validation
from bhns.experiments.core import outer_folds
from test_rxte_reconstruction import _pha_fixture

@pytest.mark.parametrize('path',['data/processed/observations.csv','results/primary_predictions.csv','configs/experiment_protocol_frozen.yaml','data/processed/validation_heasoft/../../../results/primary_predictions.csv'])
def test_primary_outputs_cannot_be_validation_targets(tmp_path,path):
    with pytest.raises(ValueError,match='validation directory'):validation_path(tmp_path,path)

def test_validation_path_is_separate(tmp_path):
    p=validation_path(tmp_path,'results/validation_heasoft/metrics.csv');assert p.parent==tmp_path/'results/validation_heasoft'

def test_validation_hash_rejects_changes(tmp_path):
    p=tmp_path/'configs/validation_heasoft_protocol.yaml';p.parent.mkdir();p.write_text('seed: 42\n');p.with_suffix('.sha256').write_text(sha256(p))
    assert validation_protocol(tmp_path)[0]['seed']==42
    p.write_text('seed: 43\n')
    with pytest.raises(ValueError,match='protocol changed'):validation_protocol(tmp_path)

@pytest.mark.parametrize('date,epoch',[('1996-03-21T18:33:59',1),('1996-03-21T18:34:00',2),('1996-04-15T23:06:00',3),('1999-03-22T17:39:00',4),('2000-05-13T00:00:00',5),('2011-12-30',5)])
def test_gain_boundaries(date,epoch):assert gain_epoch(date)==epoch

def test_gain_outside_mission_rejected():
    with pytest.raises(ValueError):gain_epoch('2025-01-01')

def test_saa_policy_is_epoch_specific():
    assert 'TIME_SINCE_SAA' in screening_expression(2)
    assert 'TIME_SINCE_SAA' not in screening_expression(3)

def test_detector_filter_and_screening(tmp_path):
    cols=[fits.Column(name='Time',format='D',array=[8.,24.,40.]),fits.Column(name='ELV',format='D',array=[20.,5.,20.]),fits.Column(name='OFFSET',format='D',array=[0.,0.,0.]),fits.Column(name='ELECTRON2',format='D',array=[.01,.01,.01])]
    cols += [fits.Column(name=f'PCU{i}_ON',format='D',array=[float(i==2)]*3) for i in range(5)]
    h=fits.BinTableHDU.from_columns(cols);h.header['TIMEDEL']=16.;p=tmp_path/'filter.fits';fits.HDUList([fits.PrimaryHDU(),h]).writeto(p)
    m=detector_samples(p,[0.],[48.],5);assert m['active_pcus']=='2';assert m['num_active_pcus']==1
    assert m['screening_retained_seconds_estimate']==32.;assert m['screening_exposure_removed_estimate']==16.

def test_common_support_needs_independent_sources_both_classes():
    rows=[]
    for c in ['BH','NS']:
        for source in range(2):
            for obs in range(2):rows.append(dict(rxte_obsid=f'{c}{source}{obs}',source_id=f'{c}{source}',class_label=c,gain_epoch=5,selected_pcus='2',exposure=500.,net_count_rate=50.,background_fraction=.1))
    f=pd.DataFrame(rows);assert len(common_support(f))==8
    f.loc[f.class_label.eq('BH'),'source_id']='one_BH';assert len(common_support(f))==0

def test_detector_diagnostic_respects_timezero_and_timepixr(tmp_path):
    fields={'Time':[0.,16.],'ELV':[20.,20.],'OFFSET':[0.,0.],'ELECTRON2':[.01,.2]}
    fields.update({f'PCU{i}_ON':[float(i==2)]*2 for i in range(5)})
    h=fits.BinTableHDU.from_columns([fits.Column(name=k,format='D',array=v) for k,v in fields.items()]);h.header.update(TIMEDEL=16.,TIMEZERO=100.,TIMEPIXR=0.)
    p=tmp_path/'filter.fits';fits.HDUList([fits.PrimaryHDU(),h]).writeto(p)
    result=detector_samples(p,[100.],[132.],5)
    assert result['screening_retained_seconds_estimate']==16.
    assert result['screening_exposure_removed_estimate']==16.

def test_common_support_rejects_bright_and_background_rows():
    rows=[dict(rxte_obsid=f'{c}{s}{o}',source_id=f'{c}{s}',class_label=c,gain_epoch=5,selected_pcus='2',exposure=500.,net_count_rate=50.,background_fraction=.1) for c in ['BH','NS'] for s in range(2) for o in range(3)]
    f=pd.DataFrame(rows);f.loc[0,'net_count_rate']=1001;f.loc[3,'background_fraction']=.6
    assert len(common_support(f))==10

def test_shape_preserves_negative_bins_and_scale_invariance():
    x=np.array([[3.,-1.,4.]]);np.testing.assert_allclose(shape_normalize(x),shape_normalize(x*100));assert shape_normalize(x)[0,1]<0
    with pytest.raises(ValueError):shape_normalize([[-1.,0.]])

def test_metadata_whitelist_excludes_target_and_amplitudes(observations):
    f=observations.copy()
    for i,k in enumerate(META_FEATURES):f[k]=np.arange(len(f))+i
    a=matrix(f,META_FEATURES);f['flux_00']=1e9;np.testing.assert_equal(matrix(f,META_FEATURES),a)
    with pytest.raises(ValueError):matrix(f,META_FEATURES+['compact_object_class'])

def test_metadata_nested_fit_and_scaler_only_see_training(observations):
    f=observations.copy()
    for i,k in enumerate(META_FEATURES):f[k]=np.arange(len(f),dtype=float)+i
    fold=outer_folds(f,'grouped')[0];p,a=fit_fold(f,fold,'logistic',META_FEATURES)
    np.testing.assert_allclose(a['scaler_mean'],f.iloc[list(fold.train)][META_FEATURES].mean().to_numpy())
    assert set(p.obs_id).isdisjoint(a['fit_obs_ids'])
    for partition in ['train','validation']:assert set(a['inner'][partition]['source_ids']).isdisjoint(a['inner']['test']['source_ids'])
    assert set(p)=={'source_id','source_name','obs_id','true_class','p_NS','p_BH'}

def test_heasoft_rate_uses_live_exposure_without_extra_pcu_division(tmp_path):
    _pha_fixture(tmp_path/'s.pha',value=400.,exposure=10.,area=1.,back=1.,stat_error=20.)
    _pha_fixture(tmp_path/'b.pha',value=100.,exposure=10.,area=1.,back=1.,stat_error=10.)
    e=fits.BinTableHDU.from_columns([fits.Column(name='CHANNEL',format='I',array=[0]),fits.Column(name='E_MIN',format='D',array=[5.]),fits.Column(name='E_MAX',format='D',array=[25.])],name='EBOUNDS')
    m=fits.BinTableHDU.from_columns([fits.Column(name='MATRIX',format='D',array=[1.])],name='SPECRESP MATRIX');fits.HDUList([fits.PrimaryHDU(),e,m]).writeto(tmp_path/'r.rsp')
    arrays,meta=heasoft_spectrum(tmp_path/'s.pha',tmp_path/'b.pha',tmp_path/'r.rsp')
    assert meta['net_count_rate']==pytest.approx(30.);assert arrays['covariance'].sum()==pytest.approx(5.);assert len(arrays['spectrum'])==43

@pytest.mark.full_workspace
def test_real_primary_is_still_immutable():
    assert verify_primary(Path(__file__).resolve().parents[1])>2000

def test_confounder_table_has_verified_row_and_source_mapping():
    root=Path(__file__).resolve().parents[1]
    primary=pd.read_csv(root/'data/processed/observations.csv');primary=primary[primary.usable]
    conf=pd.read_csv(root/'results/validation_heasoft/confounder_table.csv')
    joined=primary.merge(conf,on='rxte_obsid',validate='one_to_one',suffixes=('_primary','_diagnostic'))
    assert len(joined)==len(primary)==len(conf)
    assert joined.source_id_primary.equals(joined.source_id_diagnostic)
    assert joined.class_label_primary.equals(joined.class_label_diagnostic)
    assert set(META_FEATURES)<=set(conf)
    assert conf.num_selected_pcus.between(1,5).all()

def test_validation_predictions_round_trip_and_cache_preserve_identity(tmp_path,observations):
    p=tmp_path/'configs/validation_heasoft_protocol.yaml';p.parent.mkdir();p.write_text('seed: 42\n');p.with_suffix('.sha256').write_text(sha256(p))
    first,summary,audits=run_validation(observations,tmp_path,'test_serialization','logistic','grouped',SPECTRAL_FEATURES,fixed={'C':.1},bootstrap=False)
    restored,saved,_=run_validation(observations,tmp_path,'test_serialization','logistic','grouped',SPECTRAL_FEATURES,fixed={'C':.1},bootstrap=False)
    assert saved==summary
    pd.testing.assert_frame_equal(first.reset_index(drop=True),restored,check_exact=False,rtol=1e-12,atol=1e-12)
    assert len(audits)==5
    assert set(restored.obs_id)==set(observations.obs_id)

def test_custom_epoch_fold_declares_spectral_only_representation(observations):
    from bhns.evaluation.splits import Fold,dataset_fingerprint
    f=observations[['source_id','source_name','compact_object_class','obs_id']+SPECTRAL_FEATURES].copy()
    test=f.source_id.isin(['test-id-00','test-id-01','test-id-02','test-id-03'])
    fold=Fold(tuple(np.flatnonzero(~test)),tuple(np.flatnonzero(test)),'grouped',42,'epoch-test',dataset_fingerprint(f),representation='SM')
    pred,audit=fit_fold(f,fold,'logistic',SPECTRAL_FEATURES,fixed={'C':.1})
    assert set(pred.source_id).isdisjoint(audit['fit_source_ids'])
    assert audit['outer']['representation']=='SM'
