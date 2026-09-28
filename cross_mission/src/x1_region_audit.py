"""Exposure-map and detector-context audit of predeclared pilot apertures."""
from pathlib import Path
import json, numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1]

def main():
    dest=ROOT/'results/x1_pilot/region_figures';dest.mkdir(parents=True,exist_ok=True)
    proposals=json.loads((ROOT/'reports/region_review/proposals.json').read_text());records=[]
    for p in proposals:
        ob=p['obsid'];m=p['module'][-1];work=ROOT/f'data/processed/nustar/{ob}/x1_{m}'
        with fits.open(work/'exposure/exposure.img') as h:exposure=h[0].data.copy();eh=h[0].header.copy()
        print(ob,m,'map',exposure.shape,dict((k,eh.get(k)) for k in ['CRPIX1','CRPIX2','CRVAL1','CRVAL2','CDELT1','CDELT2','EXPOSURE','BUNIT']),flush=True)
        w=WCS(eh);direction='N' if ob=='10601308002' else 'S';b=next(x for x in p['candidates'] if x['direction']==direction)
        regions=[('source',p['source_ra'],p['source_dec'],60),('background',b['ra'],b['dec'],90)]
        sky=[];stats={};yy,xx=np.indices(exposure.shape)
        for name,ra,dec,radius in regions:
            x,y=w.all_world2pix([[ra,dec]],0)[0];rp=radius/p['pixel_scale_arcsec'];mask=(xx-x)**2+(yy-y)**2<=rp**2
            values=exposure[mask];stats[name]=dict(ra=ra,dec=dec,radius_arcsec=radius,area_arcsec2=float(np.pi*radius**2),map_pixels=int(mask.sum()),zero_exposure_fraction=float(np.mean(values<=0)),relative_exposure_percentiles=np.percentile(values/p['exposure'],[0,5,50,95,100]).tolist())
            sky.append((name,x+1,y+1,rp))
        clean=ROOT/f'data/processed/nustar/{ob}/{p["attempt"]}/clean/nu{ob}{m}01_cl.evt'
        with fits.open(clean) as h:
            d=h['EVENTS'].data;energy=1.6+.04*d['PI'];sel=(energy>=5)&(energy<=25)
            fig,axes=plt.subplots(1,3,figsize=(17,5.5),layout='constrained')
            axes[0].hist2d(d['X'][sel],d['Y'][sel],bins=np.arange(250,751,2),norm=LogNorm(vmin=1),cmap='magma')
            im=axes[1].imshow(exposure/p['exposure'],origin='lower',extent=(.5,1000.5,.5,1000.5),cmap='viridis',vmin=0,vmax=1);fig.colorbar(im,ax=axes[1],label='Usable exposure / event live exposure')
            # Detector boundaries are revealed by per-detector event positions;
            # exposure image is the quantitative active-area/gap/bad-pixel map.
            for det in range(4):
                ids=np.flatnonzero(d['DET_ID']==det)[::max(1,len(d)//15000)]
                axes[2].scatter(d['X'][ids],d['Y'][ids],s=.6,alpha=.35,label=f'DET{det}')
            for ax in axes:
                for name,x,y,rp in sky:ax.add_patch(Circle((x,y),rp,fill=False,ec='lime' if name=='source' else 'cyan',lw=1.5))
                # Catalogue marker transformed independently from event WCS.
                ra0,dec0=(84.73596816896,-64.08425498264) if ob=='10601308002' else (94.28062,9.137067)
                x0,y0=w.all_world2pix([[ra0,dec0]],1)[0];ax.plot(x0,y0,'+',color='white',markersize=9)
                ax.set(xlim=(300,700),ylim=(300,700),aspect='equal',xlabel='SKY X (pixel)',ylabel='SKY Y (pixel)')
            axes[0].set_title('5–25 keV events');axes[1].set_title('Official non-vignetted exposure');axes[2].set_title('Detector context');axes[2].legend(markerscale=5)
            fig.suptitle(f'{ob} FPM{m}: source 60″ (green), background 90″ (cyan), catalogue +')
            fig.savefig(dest/f'{ob}_{m}.png',dpi=140);plt.close(fig)
            badpix=[dict(extension=x.name,detector=x.header.get('DETNAM'),rows=len(x.data)) for x in h if x.name=='BADPIX']
        records.append(dict(obsid=ob,module='FPM'+m,regions=stats,centroid_offset_arcsec=p['centroid_offset_arcsec'],badpixel_extensions=badpix,overlap=False,review_status='AWAITING_VISUAL_REVIEW'))
    (ROOT/'results/x1_pilot/region_geometry.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2),flush=True)

if __name__=='__main__':main()
