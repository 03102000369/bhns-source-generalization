"""Retrieve original archive trees for independent PCA reduction, without primary writes."""
import argparse,concurrent.futures,hashlib,json,re,time,http.client,threading
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlsplit
import pandas as pd
from bhns.data.instrument_validation import validation_protocol

ROOT=Path(__file__).resolve().parents[1]
BASE='https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive/'
LOCAL=threading.local()

def fetch(url,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():return path.read_bytes()
    for attempt in range(3):
        try:
            parsed=urlsplit(url)
            if not hasattr(LOCAL,'connection'):
                LOCAL.connection=http.client.HTTPSConnection(parsed.netloc,timeout=60)
            LOCAL.connection.request('GET',parsed.path+('?' + parsed.query if parsed.query else ''),headers={'User-Agent':'bhns-research-validation/1.0'})
            response=LOCAL.connection.getresponse();b=response.read()
            if response.status!=200:raise OSError(f'HTTP {response.status}: {url}')
            temp=path.with_suffix(path.suffix+'.part');temp.write_bytes(b);temp.replace(path);return b
        except Exception:
            if hasattr(LOCAL,'connection'):
                LOCAL.connection.close();del LOCAL.connection
            if attempt==2:raise
            time.sleep(1)

def listing(url,path):
    h=fetch(url,path).decode('utf-8','replace')
    return [n for n in re.findall(r'href="([^"]+)"',h) if n and n[0] not in '/?.' and '/' not in n.rstrip('/')]

def one(row):
    obs=row['rxte_obsid'];dest=ROOT/'data/raw/validation_heasoft'/obs;meta=ROOT/'data/provenance/validation_heasoft/raw'/obs;meta.mkdir(parents=True,exist_ok=True)
    manifest=meta/'download_manifest.json'
    if manifest.exists():
        old=json.loads(manifest.read_text())
        if old['status']=='COMPLETE' and all(Path(x['path']).exists() and hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in old['files']):return old
    url=BASE+row['archive_identifier']+'/';records=[];errors=[]
    def download(relative):
        p=dest/relative
        try:
            b=fetch(url+relative,p);return dict(path=str(p),relative=relative,url=url+relative,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),accessed_at=datetime.now(timezone.utc).isoformat())
        except Exception as e:return dict(relative=relative,url=url+relative,error=str(e))
    try:
        names=listing(url,meta/'root_listing.html');files=[x for x in names if not x.endswith('/')]
        for d in [x for x in names if x.endswith('/') and x not in ['stdprod/','hexte/']]:
            children=listing(url+d,meta/(d.rstrip('/')+'_listing.html'))
            # Standard1/2 filenames are confirmed against archive headers after download.
            # Other PCA science modes are unnecessary; retain every PCA housekeeping file.
            if d=='pca/':children=[x for x in children if x.startswith(('FH','FS46_','FS4a_'))]
            files.extend(d+x for x in children if not x.endswith('/'))
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            for x in pool.map(download,files):
                (errors if 'error' in x else records).append(x)
    except Exception as e:errors.append(dict(error=str(e),url=url))
    result=dict(rxte_obsid=obs,source_id=row['source_id'],archive_identifier=row['archive_identifier'],status='FAILED' if errors else 'COMPLETE',files=records,errors=errors)
    manifest.write_text(json.dumps(result,indent=2));print(obs,result['status'],len(records),'files',flush=True);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);p.add_argument('--obsid');p.add_argument('--expanded',action='store_true');p.add_argument('--workers',type=int,default=4);args=p.parse_args();validation_protocol(ROOT)
    if args.expanded:f=pd.read_csv(ROOT/'data/processed/validation_heasoft/expanded_selection.csv')
    else:
        f=pd.read_csv(ROOT/'data/processed/validation_heasoft/preselected_observations.csv');s=pd.read_csv(ROOT/'data/manifests/rxte_acquisition_selection.csv')
        f=f.merge(s[['rxte_obsid','archive_identifier']],on='rxte_obsid',validate='one_to_one')
    if args.obsid:f=f[f.rxte_obsid.eq(args.obsid)]
    if args.limit:f=f.head(args.limit)
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:results=list(pool.map(one,f.to_dict('records')))
    path=ROOT/'results/validation_heasoft'/('expanded_raw_acquisition_summary.json' if args.expanded else 'raw_acquisition_summary.json')
    path.write_text(json.dumps(dict(attempted=len(results),complete=sum(r['status']=='COMPLETE' for r in results),files=sum(len(r['files']) for r in results),failed_obsids=[r['rxte_obsid'] for r in results if r['status']!='COMPLETE']),indent=2))

if __name__=='__main__':main()
