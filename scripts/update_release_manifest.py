"""Regenerate a reviewed release manifest; never use to hide unexpected changes."""
import csv,io
from release_support import ROOT,payload,sha256,describe

def update():
    origin={}
    p=ROOT/'docs/release_provenance.csv'
    if p.exists():
        with p.open(newline='') as f:origin={r['path']:r for r in csv.DictReader(f)}
    rows=[]
    for p in sorted(payload()):
        r=p.relative_to(ROOT).as_posix();phase,cat,role=describe(r)
        rows.append(dict(path=r,size_bytes=p.stat().st_size,sha256=sha256(p),phase=origin.get(r,{}).get('phase',phase),category=cat,generated_or_source='source' if r in origin and origin[r]['transformation']=='none' else 'generated_or_adapted',scientific_role=role))
    out=ROOT/'RELEASE_MANIFEST.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','size_bytes','sha256','phase','category','generated_or_source','scientific_role']);w.writeheader();w.writerows(rows)
    (ROOT/'RELEASE_MANIFEST.sha256').write_text(sha256(out)+'  RELEASE_MANIFEST.csv\n')
    return len(rows)

if __name__=='__main__':print('Manifest payload files:',update())
