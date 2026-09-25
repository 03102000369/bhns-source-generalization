"""Read-only release hash and frozen-cohort verification; no fitting or downloads."""
import csv,json,subprocess
from release_support import ROOT,payload,sha256,CONTROL

def rows(path):
    with (ROOT/path).open(newline='') as f:return list(csv.DictReader(f))

def scientific_contracts():
    obs=[r for r in rows('data/processed/observations.csv') if r['usable'].lower()=='true']
    if len(obs)!=687:raise ValueError('Primary observation count changed')
    source={}
    for r in obs:
        if r['source_id'] in source and source[r['source_id']]!=r['class_label']:raise ValueError('Inconsistent source class')
        source[r['source_id']]=r['class_label']
    if (len(source),list(source.values()).count('BH'),list(source.values()).count('NS'))!=(29,7,22):raise ValueError('Primary source census changed')
    if (sum(r['class_label']=='BH' for r in obs),sum(r['class_label']=='NS' for r in obs))!=(122,565):raise ValueError('Observation class census changed')
    state=json.loads((ROOT/'results/state_extension/stage_status.json').read_text())
    if state['ml_runs']!=0 or state['minimum_sources_per_class']!=5 or state['verdict']!='STATE_EXTENSION_CLOSED_INFEASIBLE':raise ValueError('State conclusion changed')
    if [(r['BH_sources'],r['NS_sources']) for r in state['regimes']]!=[(6,4),(2,1)]:raise ValueError('State feasibility census changed')
    return {'observations':len(obs),'sources':len(source),'BH_sources':7,'NS_sources':22,'state_matched_runs':0}

def verify(check_git=True):
    detached=(ROOT/'RELEASE_MANIFEST.sha256').read_text().strip().split('  ')
    if len(detached)!=2 or detached[1]!='RELEASE_MANIFEST.csv' or detached[0]!=sha256(ROOT/detached[1]):raise ValueError('Manifest checksum mismatch')
    listed=rows('RELEASE_MANIFEST.csv');seen=set();bad=[]
    for row in listed:
        r=row['path'];p=ROOT/r
        if r in seen:raise ValueError('Duplicate manifest path '+r)
        seen.add(r)
        try:p.resolve().relative_to(ROOT.resolve())
        except ValueError:raise ValueError('Unsafe manifest path')
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=int(row['size_bytes']) or sha256(p)!=row['sha256']:bad.append(r)
    actual={p.relative_to(ROOT).as_posix() for p in payload()}
    if seen!=actual:raise ValueError('Manifest coverage differs: '+repr(sorted(seen^actual)))
    if bad:raise ValueError('Payload mismatch: '+repr(bad))
    for r in rows('docs/release_provenance.csv'):
        if sha256(ROOT/r['path'])!=r['sha256']:raise ValueError('Copy provenance mismatch '+r['path'])
        if r['transformation']=='none' and r['sha256']!=r['original_sha256']:raise ValueError('Unchanged-copy provenance inconsistent')
    if check_git and (ROOT/'.git').exists():
        out=subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],check=True,capture_output=True).stdout
        tracked={x.decode() for x in out.split(b'\0') if x}
        if tracked and tracked!=seen|CONTROL:raise ValueError('Tracked-file manifest coverage differs: '+repr(sorted(tracked^(seen|CONTROL))))
    scientific_contracts()
    return len(listed)

if __name__=='__main__':print(json.dumps({'status':'PASS','verified_payload_files':verify(),'cohort':scientific_contracts()},indent=2))
