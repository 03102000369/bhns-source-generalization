"""Hash immutable files referenced by the current official CALDB index."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from astropy.io import fits
from evidence import ROOT, retrieve, sha256
import json

def main(stage):
    base=ROOT/'data/raw/nustar/calibration/caldb'
    with fits.open(base/'data/nustar/fpm/caldb.indx') as h:
        d=h[1].data;good=d[d['CAL_QUAL']==0]
        omitted={'2D_PSF','2D_PSF_E','MATRIX','EBOUNDS','BEABSPAR'} if stage=='pipeline' else set()
        paths=sorted({str(r['CAL_DIR'])+'/'+str(r['CAL_FILE']) for r in good if str(r['CAL_CNAM']) not in omitted})
    def get(path):
        return retrieve('https://nasa-heasarc.s3.us-east-1.amazonaws.com/caldb/'+path,'data/raw/nustar/calibration/caldb/'+path,timeout=60)
    records=[];failures=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(get,p):p for p in paths}
        for f in as_completed(futures):
            try:r=f.result();records.append(r);print(r['path'],r['bytes'],flush=True)
            except Exception as e:failures.append(dict(path=futures[f],error=repr(e)));print('FAILED',futures[f],repr(e),flush=True)
    result=dict(stage=stage,index_sha256=sha256(base/'data/nustar/fpm/caldb.indx'),files=records,failures=failures)
    (ROOT/f'data/manifests/caldb_cache_{stage}.json').write_text(json.dumps(result,indent=2)+'\n')
    if failures:raise RuntimeError('CALDB cache incomplete')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['pipeline','products']);a=p.parse_args();main(a.stage)
