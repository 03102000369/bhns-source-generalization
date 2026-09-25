"""Replay recorded public RXTE URLs outside the release; never update frozen ledgers."""
from pathlib import Path
import argparse,csv,hashlib,os,re
from urllib.parse import urlparse
from urllib.request import urlopen
from release_support import ROOT,sha256

def planned():
    with (ROOT/'data/provenance/rxte_download_manifest.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    selected=[];seen=set()
    for r in rows:
        if r['status']!='retrieved' or not re.fullmatch('[a-f0-9]{64}',r['sha256']):continue
        u=urlparse(r['url'])
        if u.scheme!='https' or u.hostname!='heasarc.gsfc.nasa.gov':raise ValueError('Non-HEASARC URL in download plan')
        if not re.fullmatch('[0-9-]+',r['rxte_obsid']):raise ValueError('Invalid ObsID')
        name=Path(u.path).name
        if not name or name in {'.','..'}:raise ValueError('Invalid product name')
        rel=Path(r['rxte_obsid'])/name
        if str(rel) in seen:raise ValueError('Duplicate output product')
        seen.add(str(rel));selected.append((r,rel))
    return selected

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--plan',action='store_true');g.add_argument('--output',type=Path);a=p.parse_args();items=planned()
    if a.plan:
        print(f'{len(items)} recorded, checksummed public products; no download performed.');return
    output=a.output.expanduser().resolve()
    if output==ROOT or ROOT in output.parents:raise ValueError('Download outside the release directory')
    for r,rel in items:
        dest=output/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if sha256(dest)!=r['sha256']:raise ValueError('Existing product hash mismatch: '+str(rel))
            continue
        part=dest.with_name(dest.name+f'.{os.getpid()}.partial')
        try:
            with urlopen(r['url'],timeout=120) as response,part.open('xb') as f:
                for b in iter(lambda:response.read(1024*1024),b''):f.write(b)
            if sha256(part)!=r['sha256']:raise ValueError('Archive checksum changed: '+str(rel))
            # Hard-link creation is atomic and refuses to overwrite a concurrent download.
            os.link(part,dest)
        finally:
            if part.exists():part.unlink()
    print(f'Checked/downloaded {len(items)} raw products outside Git.')

if __name__=='__main__':main()
