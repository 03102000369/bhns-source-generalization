import copy
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from contracts import (FEATURES,canonicalize,make_folds,validate_fold,fit_scaler,select_hyperparameters,representations,source_scores,bootstrap_indices,random_source_labels,require_both_modules,validate_product_set,require_measurement_freeze)
from evidence import ROOT,sha256
from census import key

@pytest.fixture
def identities():
    return pd.DataFrame([dict(mission=mission,obsid=f'{mission}-{source}-{i}',physical_source=source) for mission in ['RXTE','NuSTAR'] for source in list('abcdefghij') for i in range(2)])

def test_alias_known_and_unknown():
    aliases={'GX339-4':'gx_339_4','GX339M4':'gx_339_4'}
    assert canonicalize('GX 339-4',aliases)==canonicalize('GX_339m4',aliases)
    with pytest.raises(ValueError):canonicalize('GX 339+4',aliases)
    with pytest.raises(ValueError):canonicalize('GX 339-4',{'GX339-4':['one','two']})

def test_registry_alias_uniqueness():
    registry=pd.read_csv(ROOT/'data/reference/nustar_source_registry.csv').fillna('');seen={}
    for r in registry.to_dict('records'):
        for a in r['aliases'].split('|'):
            assert a
            assert key(a) not in seen or seen[key(a)]==r['source_id']
            seen[key(a)]=r['source_id']

def test_fold_complete_source_exclusion_and_serialization(identities):
    folds=make_folds(identities)
    assert folds==json.loads(json.dumps(folds))
    assert sorted(s for f in folds for s in f['test_sources'])==list('abcdefghij')
    for f in folds:
        assert not set(f['train_sources'])&set(f['test_sources'])
        assert len(f['test_obsids'])==4
        assert all(x.startswith('RXTE-') for x in f['train_obsids'])
        assert all(x.startswith('NuSTAR-') for x in f['test_obsids'])
        validate_fold(f,identities)

def test_target_labels_not_accepted_by_allocator(identities):
    for labels in [np.zeros(len(identities)),np.ones(len(identities))]:
        with pytest.raises(ValueError,match='identity columns only'):make_folds(identities.assign(label=labels))
    assert make_folds(identities)==make_folds(identities.sample(frac=1,random_state=3))

@pytest.mark.parametrize('mutation',['overlap','mission','incomplete_test','incomplete_train'])
def test_invalid_folds_fatal(identities,mutation):
    f=make_folds(identities)[0]
    if mutation=='overlap':f['train_sources'].append(f['test_sources'][0])
    if mutation=='mission':f['train_obsids'][0]=f['test_obsids'][0]
    if mutation=='incomplete_test':f['test_obsids'].pop()
    if mutation=='incomplete_train':f['train_obsids'].pop()
    with pytest.raises(ValueError):validate_fold(f,identities)

def test_duplicate_obsid_rejected(identities):
    with pytest.raises(ValueError):make_folds(pd.concat([identities,identities.iloc[:1]]))

def feature_rows():
    x=pd.DataFrame(dict(mission=['RXTE']*3,obsid=['r1','r2','r3'],physical_source=['s1','s1','s2'],label=[0,0,1]))
    for c in FEATURES['A']:x[c]=[0.,2.,10.]
    return x

def test_source_weighted_training_only_scaler():
    x=feature_rows();s,audit=fit_scaler(x,'A','RXTE',['s1','s2'])
    assert np.allclose(s.mean_,5.5)
    target=x.assign(mission='NuSTAR')
    for c in FEATURES['A']:target[c]=1e9
    # Transform does not fit, and a target row in fit is fatal.
    s.transform(target[list(FEATURES['A'])]);assert np.allclose(s.mean_,5.5)
    with pytest.raises(ValueError):fit_scaler(pd.concat([x,target]),'A','RXTE',['s1','s2'])
    with pytest.raises(ValueError):fit_scaler(x,'A','RXTE',['s1'])
    assert audit['fit_obsids']==['r1','r2','r3']

def test_feature_allowlist_excludes_identity_and_label():
    for cols in FEATURES.values():assert not set(cols)&{'mission','instrument','label','class','obsid','physical_source','ra','time'}

def test_inner_selection_mission_and_source_contract():
    x=feature_rows();c=[dict(parameters={'C':.1},inner_source_auroc=.8),dict(parameters={'C':1},inner_source_auroc=.8)]
    assert select_hyperparameters(c,x,'RXTE',['s3'])=={'C':.1}
    with pytest.raises(ValueError):select_hyperparameters(c,x.assign(mission='NuSTAR'),'RXTE',['s3'])
    with pytest.raises(ValueError):select_hyperparameters(c,x,'RXTE',['s2'])

def test_representation_fixed_per_observation_and_mission_independent():
    f=np.array([[1,2,3,4],[2,4,6,8]])*1e-10;r=representations(f)
    assert np.allclose(r['B'][0],r['B'][1])
    assert np.allclose(r['A'][1]-r['A'][0],np.log10(2))
    assert np.allclose(r['C'][0,:2],r['C'][1,:2])
    assert np.allclose(r['B'].sum(axis=1),1)
    assert np.array_equal(representations(f[:1])['A'][0],r['A'][0])

@pytest.mark.parametrize('f',[[[0,1,2,3]],[[-1,1,2,3]],[[1,2,3]],[[1,2,np.nan,4]]])
def test_invalid_flux_rejected(f):
    with pytest.raises(ValueError):representations(f)

def test_source_aggregation_is_not_observation_independence():
    x=pd.DataFrame(dict(mission=['NuSTAR']*3,obsid=['1','2','3'],physical_source=['a','a','b'],label=[0,0,1],p_ns=[.2,.8,.9]))
    out=source_scores(x)
    assert len(out)==2 and np.isclose(out.iloc[0].p_ns,.5)
    with pytest.raises(ValueError):source_scores(x.assign(label=[0,1,1]))

def test_source_bootstrap():
    table=pd.DataFrame({'physical_source':list('abcd'),'label':[0,0,1,1]})
    draws=bootstrap_indices(table,repeats=40)
    assert all(len(d)==4 and list(table.iloc[d].label).count(0)==2 for d in draws)
    assert any(len(set(d))<4 for d in draws)
    assert all(np.array_equal(a,b) for a,b in zip(draws,bootstrap_indices(table,repeats=40)))
    with pytest.raises(ValueError):bootstrap_indices(pd.concat([table,table.iloc[:1]]))

def test_random_labels_same_physical_system_across_missions(identities):
    a=random_source_labels(identities.physical_source,5);b=random_source_labels(identities.physical_source[::-1],5)
    assert a==b
    assert identities.assign(random_label=identities.physical_source.map(a)).groupby('physical_source').random_label.nunique().eq(1).all()
    assert a!=random_source_labels(identities.physical_source,6)

def test_both_modules_and_explicit_failures():
    require_both_modules({'FPMA':{'status':'COMPLETE'},'FPMB':{'status':'COMPLETE'}})
    with pytest.raises(ValueError):require_both_modules({'FPMA':{'status':'COMPLETE'}})
    with pytest.raises(ValueError):require_both_modules({'FPMA':{'status':'COMPLETE'},'FPMB':{'status':'FAILED'}})

def product_fixture(tmp_path):
    from astropy.io import fits
    paths={k:tmp_path/(k+ext) for k,ext in [('source','.pha'),('background','.pha'),('arf','.arf'),('rmf','.rmf')]}
    for kind in ['source','background']:
        h=fits.BinTableHDU.from_columns([fits.Column(name='CHANNEL',format='I',array=[0,1]),fits.Column(name='COUNTS',format='J',array=[20,25])],name='SPECTRUM')
        for k,v in {'TELESCOP':'NuSTAR','INSTRUME':'FPMA','OBS_ID':'12345678901','EXPOSURE':100,'BACKSCAL':.01,'AREASCAL':1}.items():h.header[k]=v
        if kind=='source':
            for key,k in [('BACKFILE','background'),('ANCRFILE','arf'),('RESPFILE','rmf')]:h.header[key]=paths[k].name
        fits.HDUList([fits.PrimaryHDU(),h]).writeto(paths[kind])
    grid=[fits.Column(name='ENERG_LO',format='E',array=[3,10]),fits.Column(name='ENERG_HI',format='E',array=[10,30])]
    arf=fits.BinTableHDU.from_columns(grid+[fits.Column(name='SPECRESP',format='E',array=[100,80])],name='SPECRESP')
    matrix=fits.BinTableHDU.from_columns(grid,name='MATRIX')
    for h in [arf,matrix]:h.header['TELESCOP']='NuSTAR';h.header['INSTRUME']='FPMA';h.header['CALDBVER']='20260903'
    eb=fits.BinTableHDU.from_columns([fits.Column(name='CHANNEL',format='I',array=[0,1]),fits.Column(name='E_MIN',format='E',array=[3,10]),fits.Column(name='E_MAX',format='E',array=[10,30])],name='EBOUNDS')
    fits.HDUList([fits.PrimaryHDU(),arf]).writeto(paths['arf']);fits.HDUList([fits.PrimaryHDU(),matrix,eb]).writeto(paths['rmf'])
    return paths

def test_response_and_background_pairing(tmp_path):
    from astropy.io import fits
    paths=product_fixture(tmp_path);record=validate_product_set(paths,'12345678901','FPMA')
    assert record['sha256']['rmf']==sha256(paths['rmf'])
    with fits.open(paths['background'],mode='update') as h:h['SPECTRUM'].header['OBS_ID']='99999999999'
    with pytest.raises(ValueError,match='identity mismatch'):validate_product_set(paths,'12345678901','FPMA')

@pytest.mark.parametrize('key,value',[('RESPFILE','other.rmf'),('BACKFILE','other.pha'),('ANCRFILE','other.arf'),('EXPOSURE',0)])
def test_invalid_ogip_references(tmp_path,key,value):
    from astropy.io import fits
    paths=product_fixture(tmp_path)
    with fits.open(paths['source'],mode='update') as h:h['SPECTRUM'].header[key]=value
    with pytest.raises(ValueError):validate_product_set(paths,'12345678901','FPMA')

def test_freeze_missing_forbids_ml(tmp_path):
    with pytest.raises(ValueError,match='X2 measurement freeze absent'):require_measurement_freeze(tmp_path)
    assert not (ROOT/'configs/common_representation_frozen.yaml').exists()

def test_design_lock_matches_no_performance():
    lock=json.loads((ROOT/'configs/protocol_design_lock.json').read_text())
    assert lock['protocol_sha256']==sha256(ROOT/'configs/cross_mission_protocol.yaml')
    assert lock['performance_started'] is False and lock['measurement_frozen'] is False

def test_prospective_real_census_fold_audit():
    rows=pd.read_csv(ROOT/'data/manifests/prospective_identity_rows.csv',dtype={'obsid':str})
    rec=json.loads((ROOT/'data/manifests/prospective_cross_mission_folds.json').read_text())
    assert rec['status']=='PROSPECTIVE_CENSUS_CONTRACT_ONLY_NOT_X3_PASS'
    for fold in rec['folds']:validate_fold(fold,rows)
