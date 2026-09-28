"""Synthetic numerical fixtures only; no synthetic rows enter the research table."""
import numpy as np
import pytest

from bhns.data.rxte_products import net_ogip, overlap_matrix, rebin_rates
from bhns.data.rxte_products import read_pha
from astropy.io import fits


def test_count_conservation_and_correlated_errors():
    # One native channel is split into two output bins: errors are correlated.
    y,cov,w=rebin_rates([12.],[9.],[5.],[7.],[5.,5.5,7.])
    np.testing.assert_allclose(y,[3.,9.])
    np.testing.assert_allclose(cov,[[.5625,1.6875],[1.6875,5.0625]])
    assert np.isclose(y.sum(),12.)
    assert np.isclose(cov.sum(),9.)
    assert cov.trace()<cov.sum()  # diagonal-only integration would underestimate error


def test_rebin_preserves_constant_density_across_different_grids():
    for edges in ([3.,6.,12.,30.],[3.,5.,9.,15.,25.,30.]):
        a=np.asarray(edges);rate=2*np.diff(a)
        y,_,_=rebin_rates(rate,None,a[:-1],a[1:])
        np.testing.assert_allclose(y,np.full(43,40/43))


@pytest.mark.parametrize('low,high,edges',[
    ([5.,6.],[6.,7.],[6.,5.]),([5.,6.1],[6.,7.],[5.,7.]),
    ([5.,5.9],[6.,7.],[5.,7.]),([5.1],[7.],[5.,7.]),
    ([5.],[6.],[5.,7.]),([5.],[float('nan')],[5.,7.]),
    ([5.],[5.],[5.,7.]),
])
def test_invalid_or_incomplete_grids_rejected(low,high,edges):
    with pytest.raises(ValueError):overlap_matrix(low,high,edges)


def test_background_scaling_and_variance_are_squared():
    s=dict(channels=np.array([0,1]),rate=np.array([8.,9.]),variance=np.array([4.,9.]),backscal=np.array([2.,3.]))
    b=dict(channels=np.array([0,1]),rate=np.array([1.,2.]),variance=np.array([1.,4.]),backscal=np.array([1.,6.]))
    net,var,bg=net_ogip(s,b)
    np.testing.assert_allclose(net,[6.,8.]);np.testing.assert_allclose(var,[8.,10.]);np.testing.assert_allclose(bg,[2.,1.])


def test_missing_uncertainty_never_becomes_zero():
    s=dict(channels=np.array([0]),rate=np.array([1.]),variance=None,backscal=np.array([1.]))
    b=dict(channels=np.array([0]),rate=np.array([2.]),variance=np.array([1.]),backscal=np.array([1.]))
    net,var,_=net_ogip(s,b);assert var is None
    y,cov,_=rebin_rates(net,var,[5.],[25.]);assert cov is None;assert y.sum()==pytest.approx(-1.)


def test_response_channel_order_must_match_background():
    s=dict(channels=np.array([0,1]));b=dict(channels=np.array([1,0]))
    with pytest.raises(ValueError,match='channel mismatch'):net_ogip(s,b)


@pytest.mark.parametrize('variance',[[float('nan')],[-1.],[1.,2.]])
def test_invalid_uncertainties_rejected(variance):
    with pytest.raises(ValueError):rebin_rates([1.],variance,[5.],[25.])


def _pha_fixture(path,*,kind='COUNTS',value=400.,exposure=10.,area=2.,back=2.,stat_error=20.,poisson=False):
    columns=[fits.Column(name='CHANNEL',format='I',array=[0]),fits.Column(name=kind,format='D',array=[value])]
    if stat_error is not None:columns.append(fits.Column(name='STAT_ERR',format='D',array=[stat_error]))
    h=fits.BinTableHDU.from_columns(columns,name='SPECTRUM')
    for k,v in dict(TELESCOP='XTE',INSTRUME='PCA',HDUCLASS='OGIP',EXPOSURE=exposure,AREASCAL=area,BACKSCAL=back,POISSERR=poisson,ROWID1='X1LSpecPcu2').items():h.header[k]=v
    gti=fits.BinTableHDU.from_columns([fits.Column(name='START',format='D',array=[0.]),fits.Column(name='STOP',format='D',array=[exposure])],name='STDGTI')
    fits.HDUList([fits.PrimaryHDU(),h,gti]).writeto(path)


def test_ogip_count_exposures_and_area_scalings_have_analytic_answer(tmp_path):
    _pha_fixture(tmp_path/'s.pha')
    _pha_fixture(tmp_path/'b.pha',value=100.,exposure=20.,area=4.,back=1.,stat_error=10.)
    s=read_pha(tmp_path/'s.pha');b=read_pha(tmp_path/'b.pha')
    net,var,_=net_ogip(s,b)
    np.testing.assert_allclose(net,[17.5]);np.testing.assert_allclose(var,[1.0625])


def test_ogip_rate_errors_are_not_divided_by_exposure_again(tmp_path):
    _pha_fixture(tmp_path/'rate.pha',kind='RATE',value=40.,stat_error=2.)
    p=read_pha(tmp_path/'rate.pha')
    np.testing.assert_allclose(p['rate'],[20.]);np.testing.assert_allclose(p['variance'],[1.])


@pytest.mark.parametrize('poisson',[True,False])
def test_poisson_fallback_requires_explicit_header(tmp_path,poisson):
    _pha_fixture(tmp_path/'s.pha',stat_error=None,poisson=poisson)
    p=read_pha(tmp_path/'s.pha')
    if poisson:np.testing.assert_allclose(p['variance'],[1.])
    else:assert p['variance'] is None and p['error_method']=='unavailable'


def test_negative_archive_stat_error_rejected(tmp_path):
    _pha_fixture(tmp_path/'s.pha',stat_error=-1.)
    with pytest.raises(ValueError,match='Negative STAT_ERR'):read_pha(tmp_path/'s.pha')
