import copy,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
import pytest
from astropy.io import fits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from x1_validation import validate_calibration,validate_region,response_check,product_check,gate_x1,forbid_x2_without_x1,PILOTS

@pytest.fixture
def products(tmp_path):
    def hdu(cols,name):
        h=fits.BinTableHDU.from_columns(cols,name=name);h.header.update(TELESCOP='NuSTAR',INSTRUME='FPMA');return h
    def col(name,array,fmt='E'):return fits.Column(name=name,format=fmt,array=array)
    paths={k:tmp_path/(k+'.fits') for k in ['source','background','arf','rmf']}
    e=hdu([col('CHANNEL',[0,1,2],'J'),col('E_MIN',[5,12,18]),col('E_MAX',[12,18,25])],'EBOUNDS')
    m=hdu([col('ENERG_LO',[5,12]),col('ENERG_HI',[12,25]),col('N_GRP',[1,1],'I'),col('F_CHAN',[0,0],'I'),col('N_CHAN',[3,3],'I'),col('MATRIX',np.ones((2,3))/3,'3E')],'MATRIX');m.header['DETCHANS']=3
    fits.HDUList([fits.PrimaryHDU(),m,e]).writeto(paths['rmf'])
    a=hdu([col('ENERG_LO',[5,12]),col('ENERG_HI',[12,25]),col('SPECRESP',[100,90])],'SPECRESP');fits.HDUList([fits.PrimaryHDU(),a]).writeto(paths['arf'])
    for kind in ['source','background']:
        h=hdu([col('CHANNEL',[0,1,2],'J'),col('COUNTS',[10,20,30],'J')],'SPECTRUM');h.header.update(OBS_ID=PILOTS[0],EXPOSURE=1000.,BACKSCAL=.01,AREASCAL=1.,POISSERR=True,BACKFILE=paths['background'].name,ANCRFILE=paths['arf'].name,RESPFILE=paths['rmf'].name)
        fits.HDUList([fits.PrimaryHDU(),h]).writeto(paths[kind])
    return paths

def test_valid_product_pair_and_response(products):
    r=product_check(products,PILOTS[0],'FPMA');assert r['status']=='PASS';assert r['response']['channels']==3

@pytest.mark.parametrize('mutation',['missing','module','link','counts','staterr','dim','energy','matrix','arf'])
def test_invalid_measurement_fails(products,mutation):
    if mutation=='missing':products['rmf'].unlink()
    elif mutation in ['module','link','counts','staterr']:
        with fits.open(products['source'],mode='update') as h:
            if mutation=='module':h[1].header['INSTRUME']='FPMB'
            if mutation=='link':h[1].header['RESPFILE']='unrelated.rmf'
            if mutation=='counts':h[1].data['COUNTS'][:]=0
            if mutation=='staterr':h[1].header['POISSERR']=False
    elif mutation in ['dim','energy','matrix']:
        with fits.open(products['rmf'],mode='update') as h:
            if mutation=='dim':h['MATRIX'].header['DETCHANS']=4
            if mutation=='energy':h['EBOUNDS'].data['E_MIN'][1]=30
            if mutation=='matrix':h['MATRIX'].data['MATRIX'][0,0]=np.nan
    else:
        with fits.open(products['arf'],mode='update') as h:h[1].data['SPECRESP'][0]=-1
    with pytest.raises(ValueError):product_check(products,PILOTS[0],'FPMA')

def test_calibration_provenance_and_bytes(tmp_path):
    p=tmp_path/'official.rmf';p.write_bytes(b'known immutable bytes')
    r=dict(status='ACQUIRED',url='https://nasa-heasarc.s3.us-east-1.amazonaws.com/caldb/official.rmf',local_path=p.name,size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    assert validate_calibration(r,tmp_path)
    for key,value in [('url','https://unrelated.invalid/response'),('sha256','0'*64),('status','UNAVAILABLE'),('size',0)]:
        with pytest.raises(ValueError):validate_calibration({**r,key:value},tmp_path)

@pytest.fixture
def region():
    return dict(obsid=PILOTS[0],module='FPMA',source_region='s.reg',background_region='b.reg',quality_status='PASS',source_ra=30,source_dec=0,source_radius_arcsec=60,background_ra=30.05,background_dec=0,background_radius_arcsec=90,author='geometry reviewer',timestamp_utc='2026-09-23')

def test_region_schema_and_nonoverlap(region):
    assert validate_region(region)==pytest.approx(180)
    for bad in [{**region,'background_ra':30.001},{**region,'quality_status':'PROVISIONAL'},{k:v for k,v in region.items() if k!='author'}]:
        with pytest.raises(ValueError):validate_region(bad)

def test_x1_pass_requires_all_four_and_missing_response_fails(products):
    records=[dict(obsid=o,module=m,status='PASS',region_status='PASS',response_status='PASS',event_status='PASS',lightcurve_status='PASS',paths=products) for o in PILOTS for m in ['FPMA','FPMB']]
    assert gate_x1(records)=='PASS'
    assert gate_x1(records[:3])=='BLOCKED'
    bad=copy.deepcopy(records);bad[2]['region_status']='PROVISIONAL';assert gate_x1(bad)=='BLOCKED'
    bad=copy.deepcopy(records);bad[2]['response_status']='FAIL';assert gate_x1(bad)=='BLOCKED'
    products['rmf'].unlink();assert gate_x1(records)=='BLOCKED'

def test_x2_forbidden_until_x1_pass():
    for verdict in ['BLOCKED','FAIL',None]:
        with pytest.raises(ValueError):forbid_x2_without_x1(dict(verdict=verdict))
    forbid_x2_without_x1(dict(verdict='PASS'))
