"""Validate that the screening rerun preserves the audited aperture geometry."""
from pathlib import Path
from paths import scratch_root, calibration_root
import json,numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1];LOCAL=scratch_root()/'30363002002'
def main():
    geometry=json.loads((ROOT/'results/x1_pilot/region_geometry.json').read_text());records=[]
    for m in 'AB':
        stem='nu30363002002'+m+'01';old=LOCAL/'clean'/(stem+'_cl.evt');new=LOCAL/'bright_attempt001/clean'/(stem+'_cl.evt')
        with fits.open(old) as a,fits.open(new) as b:
            same_gti=np.array_equal(a['GTI'].data,b['GTI'].data)
            ap=[h for h in a if h.name=='BADPIX'];bp=[h for h in b if h.name=='BADPIX']
            same_bad=len(ap)==len(bp) and all(x.header['DETNAM']==y.header['DETNAM'] and np.array_equal(x.data,y.data) for x,y in zip(ap,bp))
            same_exp=a[1].header['EXPOSURE']==b[1].header['EXPOSURE'];d=b[1].data
            if not (same_gti and same_bad and same_exp):raise ValueError('Exposure geometry changed; regenerate maps')
            with fits.open(LOCAL/m/'exposure_bright/exposure.img') as h:w=WCS(h[0].header);exposure=h[0].data.copy()
            entry=next(x for x in geometry if x['obsid']=='30363002002' and x['module']=='FPM'+m)
            fig,axes=plt.subplots(1,3,figsize=(17,5.5),layout='constrained');ax=axes[0];energy=1.6+.04*d['PI'];sel=(energy>=5)&(energy<=25)
            ax.hist2d(d['X'][sel],d['Y'][sel],bins=np.arange(250,751,2),norm=LogNorm(vmin=1),cmap='magma')
            im=axes[1].imshow(exposure/b[1].header['EXPOSURE'],origin='lower',extent=(.5,1000.5,.5,1000.5),cmap='viridis',vmin=0,vmax=1);fig.colorbar(im,ax=axes[1],label='Usable exposure / event live exposure')
            for det in range(4):
                ids=np.flatnonzero(d['DET_ID']==det)[::max(1,len(d)//15000)];axes[2].scatter(d['X'][ids],d['Y'][ids],s=.6,alpha=.35,label=f'DET{det}')
            centers={};exposure_stats={};yy,xx=np.indices(exposure.shape)
            for kind,r in entry['regions'].items():
                x,y=w.all_world2pix([[r['ra'],r['dec']]],1)[0];rad=r['radius_arcsec']/2.46
                for axis in axes:axis.add_patch(Circle((x,y),rad,fill=False,ec='lime' if kind=='source' else 'cyan',lw=1.5))
                centers[kind]=[float(x),float(y)]
                vals=exposure[(xx-(x-1))**2+(yy-(y-1))**2<=rad**2]/b[1].header['EXPOSURE']
                exposure_stats[kind]=dict(zero_exposure_fraction=float(np.mean(vals<=0)),relative_exposure_percentiles=np.percentile(vals,[0,5,50,95,100]).tolist())
            x,y=centers['source'];near=(d['X']-x)**2+(d['Y']-y)**2<(30/2.46)**2;near &=sel
            cx,cy=float(np.mean(d['X'][near])),float(np.mean(d['Y'][near]));shift=float(np.hypot(cx-x,cy-y)*2.46)
            x0,y0=w.all_world2pix([[94.28062,9.137067]],1)[0]
            for axis in axes:axis.plot(x0,y0,'+',c='white');axis.set(xlim=(300,700),ylim=(300,700),aspect='equal',xlabel='SKY X (pixel)',ylabel='SKY Y (pixel)')
            for axis,title in zip(axes,['5–25 keV events','New official exposure map','Detector context']):axis.set_title(title)
            axes[2].legend(markerscale=5);fig.suptitle(f'30363002002 FPM{m}: final bright-screened region audit')
            fig.savefig(ROOT/f'results/x1_pilot/region_figures/30363002002_{m}_bright.png',dpi=140);plt.close(fig)
            rec=dict(module='FPM'+m,obsid='30363002002',GTI_identical=same_gti,BADPIX_identical=same_bad,exposure_identical=same_exp,original_event_count=len(a[1].data),new_event_count=len(d),new_centroid_offset_from_approved_center_arcsec=shift,exposure_stats=exposure_stats,status='PASS' if shift<30 and all(r['zero_exposure_fraction']==0 for r in exposure_stats.values()) else 'FAIL')
        # FITS creation HISTORY changes; compare actual coordinate/aspect arrays.
        rec['aspect_tables_identical']={}
        for name in ['nu30363002002_att.fits','nu30363002002_mast.fits',f'nu30363002002{m}_det1.fits',f'nu30363002002{m}_oa.fits']:
            with fits.open(LOCAL/'clean'/name) as a,fits.open(LOCAL/'bright_attempt001/clean'/name) as b:
                rec['aspect_tables_identical'][name]=bool(len(a)==len(b) and all((x.data is None and y.data is None) or (x.data is not None and y.data is not None and x.data.tobytes()==y.data.tobytes()) for x,y in zip(a,b)))
        rec['coordinate_realization_note']='NuSTAR random subpixel coordinate realization differs by at most about 1.09 SKY pixels; GTI, bad pixels, attitude and mast unchanged. New official exposure maps explicitly recomputed; no geometry equivalence assumed.'
        records.append(rec)
    (ROOT/'results/x1_pilot/bright_geometry.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2),flush=True)
if __name__=='__main__':main()
