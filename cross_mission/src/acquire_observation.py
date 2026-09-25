"""Public HEASARC S3 mirror acquisition. Listings and bytes remain unchanged."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import json
from evidence import ROOT, retrieve
from census import archive

def acquire(obsid, download=False):
    row=archive().loc[lambda x:x.obsid.eq(obsid)].iloc[0]
    cycle=str(int(row['cycle'])).zfill(2)
    prefix=f'nustar/data/obs/{cycle}/{obsid[0]}/{obsid}/'
    url='https://nasa-heasarc.s3.amazonaws.com/?'+urlencode({'list-type':2,'prefix':prefix})
    rec=retrieve(url,f'data/raw/nustar/{obsid}/s3_listing_cycle{cycle}.xml')
    tree=ET.parse(ROOT/rec['path']);ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    assert tree.findtext('s:IsTruncated',namespaces=ns)=='false'
    entries=[]
    for e in tree.findall('s:Contents',ns):
        key=e.findtext('s:Key',namespaces=ns); size=int(e.findtext('s:Size',namespaces=ns))
        rel=key.removeprefix(prefix)
        # L1 raw, auxiliary housekeeping and supplied screening diagnostics.
        selected=rel.split('/')[0] in {'event_uf','auxil','hk'}
        entries.append(dict(key=key,relative_path=rel,bytes=size,selected=selected,url='https://nasa-heasarc.s3.amazonaws.com/'+key))
    (ROOT/f'data/manifests/archive_files_{obsid}.json').write_text(json.dumps(entries,indent=2)+'\n')
    selected=[e for e in entries if e['selected'] and e['bytes']>0]
    if not selected:
        raise RuntimeError('No raw files at verified-cycle archive prefix: '+prefix)
    print(obsid,'files',len(entries),'raw files',len(selected),'MiB',sum(e['bytes'] for e in selected)/2**20,flush=True)
    if download:
        def get(e):
            rec=retrieve(e['url'],f'data/raw/nustar/{obsid}/'+e['relative_path'])
            if rec['bytes']!=e['bytes']:raise ValueError('Length mismatch '+e['key'])
            print(e['relative_path'],rec['bytes'],flush=True)
            return rec
        with ThreadPoolExecutor(max_workers=4) as pool:downloads=list(pool.map(get,selected))
        (ROOT/f'data/manifests/download_{obsid}.json').write_text(json.dumps(downloads,indent=2)+'\n')
    return entries

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('obsid');p.add_argument('--download',action='store_true');args=p.parse_args()
    acquire(args.obsid,args.download)
