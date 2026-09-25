"""Synthetic numerical tests only; no astronomical inference or classifier."""
from pathlib import Path
import sys,inspect
import numpy as np
import pytest
from scipy.optimize import minimize_scalar
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from x2_measurement import Measurement,basis,integration,profile_background,poisson_deviance,features,group_channels,NODES

def test_photon_continuum_and_integrals_recover_powerlaw():
    e,w,ids=integration(np.array([3.,5.,12.]),np.array([5.,12.,40.]),order=32)
    norm=.01;theta=np.log(norm)-2*np.log(NODES)
    assert np.exp(basis(e)@theta)==pytest.approx(norm/e**2,rel=1e-12)
    actual=np.bincount(ids,weights=w*np.exp(basis(e)@theta))
    assert actual==pytest.approx(norm*(1/np.array([3.,5.,12.])-1/np.array([5.,12.,40.])),rel=1e-10)

@pytest.mark.parametrize('s,b,m,alpha',[(100,20,80,.4),(0,0,1,.5),(12,0,3,.5),(0,20,4,.4),(100,0,100,.5)])
def test_profile_background_matches_direct_poisson_likelihood(s,b,m,alpha):
    prof=float(profile_background(np.array([s]),np.array([b]),np.array([m]),alpha)[0])
    def fun(x):return poisson_deviance(np.array([s]),np.array([m+alpha*x]))+poisson_deviance(np.array([b]),np.array([x]))
    direct=minimize_scalar(fun,bounds=(0,max(1000,s+b)),method='bounded',options={'xatol':1e-10})
    assert fun(prof)<=direct.fun+1e-7

def test_grouping_conserves_source_background_and_band_edges():
    e=np.arange(5.02,25,.04);b=np.ones(len(e));g=group_channels(b,e,5)
    assert np.allclose(np.asarray(g.sum(axis=0)),1)
    assert np.sum(g@b)==pytest.approx(b.sum())
    for row in g:
        bands=np.searchsorted(NODES,e[row.indices],side='right')
        assert len(set(bands))==1

def test_feature_generation_is_independent_of_class_labels_and_metadata():
    flux=np.array([1.,2.,3.,4.])*1e-10;cov=np.diag((flux*.1)**2)
    before=features(flux,cov)
    # Only allowed numerical arrays reach the interface, regardless of metadata.
    for labels in [['BH','NS'],['NS','BH'],['arbitrary','values']]:
        rows=[dict(class_label=v,flux=flux.copy(),covariance=cov.copy()) for v in labels]
        for row in rows:
            after=features(row['flux'],row['covariance'])
            for name in before:np.testing.assert_array_equal(before[name]['values'],after[name]['values'])
    assert set(inspect.signature(features).parameters)=={'flux','covariance'}
    with pytest.raises(ValueError):Measurement(dict(source='s',background='b',rmf='r',arf='a',class_label='BH'))

def test_flux_fraction_uncertainty_respects_sum_constraint():
    f=np.array([1.,2.,3.,4.]);r=features(f,np.eye(4)*.01)
    assert r['B']['values'].sum()==pytest.approx(1)
    assert r['B']['covariance'].sum()==pytest.approx(0,abs=1e-14)
    assert np.all(r['A']['sigma']>0)
