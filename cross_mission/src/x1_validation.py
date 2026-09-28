"""Hard X1 measurement gates; contains no class labels or classifiers."""
from pathlib import Path
import csv,hashlib,json,math,io,subprocess
import numpy as np
from astropy.io import fits
ROOT=Path(__file__).resolve().parents[1]
PILOTS=('10601308002','30363002002')

def stable_read(path):
    """Bounded fresh native reader; never accept File Provider's empty reads."""
    p=Path(path);size=p.stat().st_size
    for timeout in [3,10,30,30]:
        try:
            r=subprocess.run(['/usr/bin/perl','-e','open(my $f,"<",$ARGV[0]) or die $!; binmode $f; binmode STDOUT; while(my $n=read($f,my $b,1048576)){print $b}',str(p)],capture_output=True,check=True,timeout=timeout)
            if len(r.stdout)==size and size>0:return r.stdout
        except subprocess.SubprocessError:pass
    raise ValueError('Incomplete or unavailable local byte read: '+str(p))

def sha(path):return hashlib.sha256(stable_read(path)).hexdigest()

def open_fits(path):return fits.open(io.BytesIO(stable_read(path)),memmap=False)

def validate_calibration(record,root=ROOT):
    if record.get('status')!='ACQUIRED':raise ValueError('Calibration unavailable')
    if not record['url'].startswith(('https://nasa-heasarc.s3.us-east-1.amazonaws.com/caldb/','https://heasarc.gsfc.nasa.gov/FTP/caldb/')):raise ValueError('Unofficial calibration source')
    p=Path(root)/record['local_path']
    if not p.is_file() or p.stat().st_size!=int(record['size']) or sha(p)!=record['sha256']:raise ValueError('Calibration provenance mismatch')
    return True

def validate_region(record):
    required={'obsid','module','source_region','background_region','quality_status','source_ra','source_dec','source_radius_arcsec','background_ra','background_dec','background_radius_arcsec','author','timestamp_utc'}
    if not required<=record.keys():raise ValueError('Region manifest schema incomplete')
    if record['quality_status']!='PASS':raise ValueError('Provisional or rejected region')
    a,b,c,d=np.radians([float(record[k]) for k in ['source_ra','source_dec','background_ra','background_dec']])
    sep=2*np.arcsin(np.sqrt(np.clip(np.sin((d-b)/2)**2+np.cos(b)*np.cos(d)*np.sin((c-a)/2)**2,0,1)))*180/np.pi*3600
    radii=[float(record[k]) for k in ['source_radius_arcsec','background_radius_arcsec']]
    if not all(np.isfinite(radii)) or min(radii)<=0 or sep<=sum(radii):raise ValueError('Invalid or overlapping regions')
    return float(sep)

def energy_grid(lo,hi):
    if not (np.isfinite(lo).all() and np.isfinite(hi).all() and np.all(hi>lo) and np.all(np.diff(lo)>0) and np.all(np.diff(hi)>0)):raise ValueError('Invalid energy grid')

def response_check(rmf,arf,module):
    with open_fits(rmf) as rh,open_fits(arf) as ah:
        m=rh['MATRIX'];e=rh['EBOUNDS'];a=ah['SPECRESP'];nch=len(e.data)
        for hdu in [m,e,a]:
            if hdu.header.get('TELESCOP','').upper()!='NUSTAR' or hdu.header.get('INSTRUME')!=module:raise ValueError('Wrong response module')
        energy_grid(e.data['E_MIN'],e.data['E_MAX']);energy_grid(m.data['ENERG_LO'],m.data['ENERG_HI']);energy_grid(a.data['ENERG_LO'],a.data['ENERG_HI'])
        if not np.array_equal(e.data['CHANNEL'],np.arange(e.data['CHANNEL'][0],e.data['CHANNEL'][0]+nch)):raise ValueError('Noncontiguous response channels')
        if int(m.header['DETCHANS'])!=nch:raise ValueError('RMF channel dimension mismatch')
        if len(a.data)!=len(m.data) or not np.allclose(a.data['ENERG_LO'],m.data['ENERG_LO']) or not np.allclose(a.data['ENERG_HI'],m.data['ENERG_HI']):raise ValueError('ARF/RMF grid mismatch')
        area=np.asarray(a.data['SPECRESP']);common=(m.data['ENERG_LO']>=5)&(m.data['ENERG_HI']<=25)
        if not np.isfinite(area).all() or (area<0).any() or not np.all(area[common]>0):raise ValueError('Invalid ARF effective area')
        norms=[]
        for row in m.data:
            ng=int(row['N_GRP']);starts=np.atleast_1d(row['F_CHAN'])[:ng];widths=np.atleast_1d(row['N_CHAN'])[:ng]
            if ng<0 or len(starts)!=ng or len(widths)!=ng or np.any(widths<=0):raise ValueError('Invalid RMF groups')
            if np.any(starts<e.data['CHANNEL'][0]) or np.any(starts+widths>e.data['CHANNEL'][-1]+1):raise ValueError('RMF channel bounds invalid')
            values=np.asarray(row['MATRIX']).ravel()
            if len(values)<sum(widths) or not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid RMF matrix')
            norms.append(float(values[:sum(widths)].sum()))
        if not np.all(np.asarray(norms)[common]>0):raise ValueError('Zero response in common energy domain')
        if e.data['E_MIN'].min()>5 or e.data['E_MAX'].max()<25:raise ValueError('Common domain unsupported')
        return dict(status='PASS',channels=nch,matrix_rows=len(m.data),energy_min_keV=float(e.data['E_MIN'].min()),energy_max_keV=float(e.data['E_MAX'].max()),arf_min_5_25=float(area[common].min()),rmf_row_sum_min_5_25=float(np.asarray(norms)[common].min()),rmf_sha256=sha(rmf),arf_sha256=sha(arf))

def product_check(paths,obs,module):
    if set(paths)!={'source','background','arf','rmf'} or not all(Path(p).is_file() for p in paths.values()):raise ValueError('Complete real product set required')
    response=response_check(paths['rmf'],paths['arf'],module)
    with open_fits(paths['source']) as s,open_fits(paths['background']) as b,open_fits(paths['rmf']) as r:
        a=s['SPECTRUM'];d=b['SPECTRUM'];eb=r['EBOUNDS'].data
        for spec in [a,d]:
            for key,value in [('OBS_ID',obs),('TELESCOP','NUSTAR'),('INSTRUME',module)]:
                if str(spec.header.get(key,'')).upper()!=value.upper():raise ValueError('Spectrum identity mismatch '+key)
            for key in ['EXPOSURE','BACKSCAL','AREASCAL']:
                if not np.isfinite(spec.header.get(key,1)) or spec.header.get(key,1)<=0:raise ValueError('Invalid spectrum scale '+key)
            counts=np.asarray(spec.data['COUNTS'])
            if not np.isfinite(counts).all() or (counts<0).any():raise ValueError('Invalid counts')
            if not spec.header.get('POISSERR',False) and 'STAT_ERR' not in spec.columns.names:raise ValueError('Missing statistical errors')
            if 'STAT_ERR' in spec.columns.names and (not np.isfinite(spec.data['STAT_ERR']).all() or (spec.data['STAT_ERR']<0).any()):raise ValueError('Invalid statistical errors')
            if not np.array_equal(spec.data['CHANNEL'],eb['CHANNEL']):raise ValueError('Spectrum response dimension mismatch')
        for key,kind in [('BACKFILE','background'),('ANCRFILE','arf'),('RESPFILE','rmf')]:
            if Path(a.header.get(key,'')).name!=Path(paths[kind]).name:raise ValueError('Broken OGIP linkage '+key)
        if a.data['COUNTS'].sum()<=0:raise ValueError('Empty source spectrum')
        bands=[(5,8),(8,12),(12,18),(18,25),(5,25)];diagnostics={}
        alpha=a.header['EXPOSURE']/d.header['EXPOSURE']*a.header['BACKSCAL']/d.header['BACKSCAL']
        for lo,hi in bands:
            mask=(eb['E_MIN']>=lo-1e-5)&(eb['E_MAX']<=hi+1e-5);sc=float(a.data['COUNTS'][mask].sum());bc=float(d.data['COUNTS'][mask].sum());net=sc-alpha*bc;variance=sc+alpha**2*bc
            diagnostics[f'{lo}_{hi}']=dict(source_counts=sc,background_counts=bc,background_fraction=alpha*bc/sc if sc else None,net_rate=net/a.header['EXPOSURE'],net_rate_error=np.sqrt(variance)/a.header['EXPOSURE'],net_significance=net/np.sqrt(variance) if variance>0 else None,channels=int(mask.sum()))
        return dict(obsid=obs,module=module,status='PASS',exposure=float(a.header['EXPOSURE']),background_exposure=float(d.header['EXPOSURE']),source_counts=int(a.data['COUNTS'].sum()),background_counts=int(d.data['COUNTS'].sum()),background_scaling=float(alpha),paths={k:str(Path(v).resolve()) for k,v in paths.items()},hashes={k:sha(v) for k,v in paths.items()},response=response,bands=diagnostics)

def gate_x1(records):
    expected={(o,m) for o in PILOTS for m in ['FPMA','FPMB']}
    if len(records)!=4 or {(r['obsid'],r['module']) for r in records}!=expected:return 'BLOCKED'
    for r in records:
        if any(r.get(k)!='PASS' for k in ['status','region_status','response_status','event_status','lightcurve_status']):return 'BLOCKED'
        if set(r.get('paths',{}))!={'source','background','arf','rmf'} or not all(Path(p).is_file() for p in r['paths'].values()):return 'BLOCKED'
    return 'PASS'

def forbid_x2_without_x1(report):
    if report.get('verdict')!='PASS':raise ValueError('X1 not PASS; X2 forbidden')
