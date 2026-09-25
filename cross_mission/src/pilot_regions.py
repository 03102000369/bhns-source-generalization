"""Label-blind engineering aperture proposals; images require explicit review."""
import json
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
from evidence import ROOT, sha256

PILOTS = [('10601308002', 'attempt002', 84.73596816896, -64.08425498264),
          ('30363002002', 'attempt003', 94.28062, 9.137067)]

def main():
    out = ROOT/'reports/region_review'; out.mkdir(exist_ok=True)
    records=[]
    for obs, attempt, ra, dec in PILOTS:
        for mod in 'AB':
            path=ROOT/f'data/processed/nustar/{obs}/{attempt}/clean/nu{obs}{mod}01_cl.evt'
            with fits.open(path) as hd:
                h=hd['EVENTS'].header; d=hd['EVENTS'].data
                xi=list(d.names).index('X')+1; yi=list(d.names).index('Y')+1
                w=WCS(naxis=2)
                w.wcs.crpix=[h[f'TCRPX{xi}'],h[f'TCRPX{yi}']]
                w.wcs.crval=[h[f'TCRVL{xi}'],h[f'TCRVL{yi}']]
                w.wcs.cdelt=[h[f'TCDLT{xi}'],h[f'TCDLT{yi}']]
                w.wcs.ctype=['RA---TAN','DEC--TAN']
                x,y=w.all_world2pix([[ra,dec]],1)[0]; scale=abs(w.wcs.cdelt[0])*3600
                energy=1.6+0.04*d['PI']; band=(energy>=5)&(energy<=25)
                nearby=band&((d['X']-x)**2+(d['Y']-y)**2<(30/scale)**2)
                cx=float(np.mean(d['X'][nearby]));cy=float(np.mean(d['Y'][nearby]))
                offset=float(np.hypot(cx-x,cy-y)*scale)
                if not np.isfinite(offset) or offset>30:raise ValueError('Centroid requires identity review')
                cra,cdec=w.all_pix2world([[cx,cy]],1)[0]
                candidates=[('E',cx-180/scale,cy),('N',cx,cy+180/scale),('W',cx+180/scale,cy),('S',cx,cy-180/scale)]
                fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
                for ax,mask,title in [(axes[0],band,'5–25 keV'),(axes[1],np.ones(len(d),dtype=bool),'All clean event energies')]:
                    ax.hist2d(d['X'][mask],d['Y'][mask],bins=np.arange(300,701,3),norm=LogNorm(vmin=1),cmap='magma')
                    ax.add_patch(Circle((cx,cy),60/scale,fill=False,ec='lime',lw=1.6))
                    for label,bx,by in candidates:
                        ax.add_patch(Circle((bx,by),90/scale,fill=False,ec='cyan',lw=1));ax.text(bx,by,label,color='cyan')
                    ax.set(xlim=(300,700),ylim=(300,700),aspect='equal',title=f'{obs} FPM{mod}: {title}',xlabel='SKY X (pixel)',ylabel='SKY Y (pixel)')
                fig.savefig(out/f'{obs}_{mod}_proposals.png',dpi=130);plt.close(fig)
                detsummary={}
                for label,bx,by in [('source',cx,cy),*candidates]:
                    rad=60 if label=='source' else 90
                    mask=band&((d['X']-bx)**2+(d['Y']-by)**2<(rad/scale)**2)
                    detsummary[label]={str(int(k)):int(v) for k,v in zip(*np.unique(d['DET_ID'][mask],return_counts=True))}
                records.append(dict(obsid=obs,attempt=attempt,module='FPM'+mod,event_sha256=sha256(path),exposure=float(h['EXPOSURE']),ontime=float(h['ONTIME']),events=len(d),source_ra=float(cra),source_dec=float(cdec),centroid_offset_arcsec=offset,source_x=cx,source_y=cy,pixel_scale_arcsec=scale,candidates=[dict(direction=label,ra=float(w.all_pix2world([[bx,by]],1)[0][0]),dec=float(w.all_pix2world([[bx,by]],1)[0][1]),x=bx,y=by) for label,bx,by in candidates],band_event_detectors=detsummary))
    (out/'proposals.json').write_text(json.dumps(records,indent=2)+'\n')

if __name__=='__main__':main()
