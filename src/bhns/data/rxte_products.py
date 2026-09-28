"""OGIP postprocessing of mission-generated PCA spectra, never raw-event reduction.

Detector-space recorded rates are not unfolded photon flux. Native counts,
response boundaries and propagated rebin covariance are retained separately.
"""
import hashlib
import re
from pathlib import Path
from datetime import datetime

from astropy.io import fits
import numpy as np


REPRESENTATION = 'PCA_OGIP_RATE43_OVERLAP_V1'
ENERGY_EDGES = np.linspace(5., 25., 44)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def designation_key(name):
    return re.sub(r'[\s_]', '', str(name)).upper()


def overlap_matrix(low, high, edges):
    """Conserve integrated counts assuming constant density inside each native bin.

    This named histogram transformation is a detector-space representation,
    not an interpolation of spectral centers or an inverse response operation.
    """
    low,high,edges=map(lambda x:np.asarray(x,dtype=float),(low,high,edges))
    if low.ndim!=1 or high.shape!=low.shape or edges.ndim!=1 or len(edges)<2:
        raise ValueError('Invalid energy-boundary dimensions')
    if not all(np.isfinite(x).all() for x in (low,high,edges)) or np.any(high<=low) or np.any(np.diff(edges)<=0):
        raise ValueError('Nonfinite or unordered energy boundaries')
    if np.any(low[1:]<high[:-1]-1e-5) or not np.allclose(low[1:],high[:-1],atol=1e-5,rtol=0):
        raise ValueError('Native energy grid has gaps or overlap')
    if low[0]>edges[0] or high[-1]<edges[-1]:
        raise ValueError('Response does not cover requested energy band')
    return np.maximum(0.,np.minimum(edges[1:,None],high)-np.maximum(edges[:-1,None],low))/(high-low)


def rebin_rates(rate, variance, low, high, edges=ENERGY_EDGES):
    weights=overlap_matrix(low,high,edges)
    rate=np.asarray(rate,float)
    if rate.shape!=(weights.shape[1],) or not np.isfinite(rate).all():raise ValueError('Invalid rate vector')
    result=weights@rate
    if variance is None:return result,None,weights
    variance=np.asarray(variance,float)
    if variance.shape!=rate.shape or not np.isfinite(variance).all() or np.any(variance<0):raise ValueError('Invalid variance vector')
    covariance=(weights*variance[None,:])@weights.T
    return result,covariance,weights


def _column(data,header,name,default=None):
    if name in data.names:values=np.asarray(data[name],float)
    elif name in header:values=np.full(len(data),float(header[name]))
    elif default is not None:values=np.full(len(data),float(default))
    else:raise ValueError(f'Missing OGIP {name}')
    if values.shape!=(len(data),) or not np.isfinite(values).all():raise ValueError(f'Invalid OGIP {name}')
    return values


def read_pha(path):
    with fits.open(path,memmap=False) as hdus:
        h=hdus['SPECTRUM']; data=h.data; header=h.header.copy()
        if header.get('TELESCOP')!='XTE' or header.get('INSTRUME')!='PCA' or header.get('HDUCLASS')!='OGIP':
            raise ValueError('Not an OGIP RXTE/PCA spectrum')
        if not np.isfinite(header.get('EXPOSURE',np.nan)) or header['EXPOSURE']<=0:raise ValueError('Invalid exposure')
        channels=np.asarray(data['CHANNEL'],int)
        if len(set(channels))!=len(channels) or np.any(np.diff(channels)<=0):raise ValueError('Unordered or duplicate channels')
        kind='COUNTS' if 'COUNTS' in data.names else 'RATE'
        values=_column(data,header,kind)
        divisor=float(header['EXPOSURE']) if kind=='COUNTS' else 1.
        if 'STAT_ERR' in data.names:
            err=_column(data,header,'STAT_ERR'); error_method='archive_STAT_ERR'
            if np.any(err<0):raise ValueError('Negative STAT_ERR')
        elif bool(header.get('POISSERR',False)) and kind=='COUNTS' and np.all(values>=0):
            err=np.sqrt(values);error_method='explicit_POISSERR_counts'
        else:err=None;error_method='unavailable'
        area=_column(data,header,'AREASCAL');back=_column(data,header,'BACKSCAL')
        if np.any(area<=0) or np.any(back<=0):raise ValueError('Nonpositive area/background scaling')
        rate=values/divisor/area
        variance=None if err is None else (err/divisor/area)**2
        pcus=sorted({int(m.group(1)) for k,v in header.items() if k.startswith('ROWID') for m in [re.search(r'Pcu([0-4])',str(v))] if m})
        gti=hdus['STDGTI'].data
        starts=np.asarray(gti['START'],float);stops=np.asarray(gti['STOP'],float)
        if not len(starts) or np.any(stops<=starts):raise ValueError('Invalid GTIs')
        return dict(header=header,channels=channels,values=values,rate=rate,variance=variance,backscal=back,
                    quality=_column(data,header,'QUALITY',0),syserr=_column(data,header,'SYS_ERR',0),
                    pcus=pcus,starts=starts,stops=stops,error_method=error_method,format=kind,
                    hdu_structure=[dict(name=x.name,rows=0 if x.data is None else len(x.data)) for x in hdus])


def net_ogip(source,background):
    """XSPEC data-minus-scaled-background rates and independent statistical variance."""
    if not np.array_equal(source['channels'],background['channels']):raise ValueError('Source/background channel mismatch')
    scale=source['backscal']/background['backscal']
    back=scale*background['rate']
    variance=None if source['variance'] is None or background['variance'] is None else source['variance']+scale**2*background['variance']
    return source['rate']-back,variance,back


def process_products(records, observation, aliases):
    products={r['product_type']:r for r in records if r['status']=='retrieved'}
    for kind in ['source','background','response','lightcurve','filter']:
        if kind not in products:raise ValueError(f'Missing retrieved {kind} product')
        if sha256(products[kind]['path'])!=products[kind]['sha256']:raise ValueError(f'{kind} checksum mismatch')
    source=read_pha(products['source']['path']);background=read_pha(products['background']['path'])
    sh,bh=source['header'],background['header'];obs=observation['rxte_obsid']
    for header in [sh,bh]:
        if designation_key(header.get('OBJECT','')) not in {designation_key(a) for a in aliases}:
            raise ValueError('FITS OBJECT is not a reviewed source designation')
    source_files=[str(v) for k,v in sh.items() if re.fullmatch(r'FILEN\d+',k)]
    background_files=[str(v) for k,v in bh.items() if re.fullmatch(r'FILEN\d+',k)]
    if not source_files or any(obs not in p for p in source_files):raise ValueError('Source FITS extraction history does not bind the ObsID')
    if {Path(p).name for p in background_files}!={Path(p).name+'_bkg' for p in source_files}:
        raise ValueError('Background modeled-input filenames do not match source files')
    for header in [sh,bh]:
        if abs(float(header['RA_OBJ'])-float(observation['ra']))>.005 or abs(float(header['DEC_OBJ'])-float(observation['dec']))>.005:
            raise ValueError('FITS pointing differs from verified archive position')
    if sh.get('BACKFILE')!=products['background']['filename'].removesuffix('.gz') or sh.get('RESPFILE')!=products['response']['filename'].removesuffix('.gz'):
        raise ValueError('OGIP linked background/response filename mismatch')
    if sh.get('CORRFILE','NONE')!='NONE' or sh.get('ANCRFILE','NONE')!='NONE':raise ValueError('Additional calibration product required')
    if source['pcus']!=background['pcus'] or not source['pcus']:raise ValueError('Detector selection mismatch or unavailable')
    if source['starts'].shape!=background['starts'].shape or not np.allclose(source['starts'],background['starts'],atol=1e-6,rtol=0) or not np.allclose(source['stops'],background['stops'],atol=1e-6,rtol=0):
        raise ValueError('Source/background GTI mismatch (tolerance one microsecond)')
    # SAEXTRCT spectra contain summed ROWID counts, not fcalc-normalized light-curve rates.
    # Require on-time exposure, integer source counts and matching statistical definition.
    ontime=float(np.sum(source['stops']-source['starts']))
    if not np.isclose(sh['EXPOSURE'],ontime,rtol=1e-5) or not np.isclose(bh['EXPOSURE'],ontime,rtol=1e-5):
        raise ValueError('Exposure convention requires separate calibration review')
    if 'SAEXTRCT' not in sh.get('CREATOR','') or source['format']!='COUNTS' or not np.allclose(source['values'],np.round(source['values']),rtol=0,atol=1e-5):
        raise ValueError('Unverified summed-detector normalization convention')
    with fits.open(products['filter']['path'],memmap=False) as hdus:
        data=hdus[1].data; times=np.asarray(data['Time'],float); good=np.zeros(len(times),bool)
        for start,stop in zip(source['starts'],source['stops']):good|=(times>=start)&(times<stop)
        if not good.any():raise ValueError('Filter file does not sample source GTIs')
        selected_on={str(p):float(np.mean(data[f'PCU{p}_ON'][good])) for p in source['pcus']}
        if any(not np.isfinite(v) or v<.999 for v in selected_on.values()):raise ValueError('Selected PCUs not continuously on in sampled GTIs; re-extraction required')
        def diagnostic(column,operation):
            values=np.asarray(data[column][good],float);valid=np.isfinite(values)
            return dict(value=float(operation(values[valid])) if valid.any() else None,finite_fraction=float(valid.mean()))
        filter_meta=dict(selected_pcu_on_fractions=selected_on,filter_samples_in_gti=int(good.sum()),
                         electron2_max=diagnostic('ELECTRON2',np.max),
                         minimum_elevation=diagnostic('ELV',np.min),maximum_offset=diagnostic('OFFSET',np.max))
    with fits.open(products['lightcurve']['path'],memmap=False) as hdus:
        lh=hdus['RATE'].header
        lcmeta=dict(deadapp=bool(lh.get('DEADAPP',False)),normalization_history=list(lh.get('HISTORY',[])),
                    rowids=[str(v) for k,v in lh.items() if k.startswith('ROWID')])
    with fits.open(products['response']['path'],memmap=False) as hdus:
        bounds=hdus['EBOUNDS'];low=np.asarray(bounds.data['E_MIN'],float);high=np.asarray(bounds.data['E_MAX'],float)
        if not np.array_equal(bounds.data['CHANNEL'],source['channels']):raise ValueError('Response/channel mismatch')
        if bounds.header.get('INSTRUME')!='PCA':raise ValueError('Response instrument mismatch')
        matrix=hdus['SPECRESP MATRIX'];flat=np.concatenate([np.asarray(a,float).ravel() for a in matrix.data['MATRIX']])
        if not np.isfinite(flat).all() or np.any(flat<0) or not np.any(flat>0):raise ValueError('Invalid response matrix')
        calmeta=dict(creator=matrix.header.get('CREATOR'),date=matrix.header.get('DATE'),history=list(matrix.header.get('HISTORY',[])),
                     calibration_identifier=products['response']['sha256'],response_rows=len(matrix.data))
    rate,variance,back=net_ogip(source,background)
    npcu=len(source['pcus']);rate/=npcu;back/=npcu
    if variance is not None:variance/=npcu**2
    vector,covariance,weights=rebin_rates(rate,variance,low,high)
    used=weights.sum(axis=0)>0
    if np.any(source['quality'][used]!=0) or np.any(background['quality'][used]!=0):raise ValueError('Nonzero OGIP quality in analysis band')
    src_rate=float((weights@(source['rate']/npcu)).sum());bg_rate=float((weights@back).sum())
    date_obs=sh['DATE-OBS']
    if '/' in date_obs:date_obs=datetime.strptime(date_obs,'%d/%m/%y').strftime('%Y-%m-%d')+'T'+sh.get('TIME-OBS','00:00:00')
    metadata=dict(representation=REPRESENTATION,rxte_obsid=obs,object=sh['OBJECT'],date_obs=date_obs,date_end=sh['DATE-END'],
        exposure=sh['EXPOSURE'],gti_seconds=ontime,pcus=source['pcus'],pcu_normalization=npcu,
        units='recorded count/s/selected PCU/output bin',deadtime_status='NOT_CORRECTED',
        source_count_rate=src_rate,background_count_rate=bg_rate,net_count_rate=float(vector.sum()),
        errors_available=covariance is not None,source_error_method=source['error_method'],background_error_method=background['error_method'],
        native_channels_used=int(used.sum()),native_min_keV=float(low[used][0]),native_max_keV=float(high[used][-1]),
        grid_id=hashlib.sha256(np.column_stack([low,high]).astype('<f8').tobytes()).hexdigest(),
        hdu_structure=source['hdu_structure'],native_format=source['format'],source_creator=sh.get('CREATOR'),pipeline_version=sh.get('RXTESP'),
        source_systematics_max=float(source['syserr'].max()),background_systematics_max=float(background['syserr'].max()),
        filter_metadata=filter_meta,lightcurve_metadata=lcmeta,response_metadata=calmeta)
    arrays=dict(native_channels=source['channels'],native_low_keV=low,native_high_keV=high,native_net_rate=rate,
                native_source_counts=source['values'],native_background_counts=background['values'],
                energy_edges_keV=ENERGY_EDGES,overlap_weights=weights,spectrum=vector)
    if covariance is not None:arrays.update(native_variance=variance,covariance=covariance,error=np.sqrt(np.diag(covariance)))
    return metadata,arrays
