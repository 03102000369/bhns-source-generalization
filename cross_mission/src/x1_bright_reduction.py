"""Reprocess the locked bright-bin trigger with official spectroscopy screening."""
from pathlib import Path
from paths import scratch_root, calibration_root
import concurrent.futures, datetime, gzip, hashlib, json, os, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
LOCAL=scratch_root()
OBS='30363002002'
EXPR='(STATUS==b0000xxx00xxxx000)&&(SHIELD==0)'
def sha(p):
    return subprocess.run(['shasum','-a','256',str(p)],check=True,capture_output=True,text=True,timeout=60).stdout.split()[0]
def copy_verified(src,dst,expected):
    dst.parent.mkdir(parents=True,exist_ok=True)
    for _ in range(3):
        try:
            subprocess.run(['cp',str(src),str(dst)],check=True,timeout=60)
            if sha(dst)==expected:return
        except subprocess.SubprocessError:pass
    raise ValueError('Input staging failure: '+str(src))
def main():
    work=LOCAL/OBS/'bright_attempt001';saved=ROOT/f'data/processed/nustar/{OBS}/x1_bright_attempt001'
    if work.exists() or saved.exists():raise ValueError('Preserve existing attempts')
    work.mkdir(parents=True);records=[]
    # Use the explicitly installed official CALDB; never copy workstation caches.
    calibration_root()
    manifest=json.loads((ROOT/f'data/manifests/download_{OBS}.json').read_text())
    def stage(x):
        src=ROOT/x['path'];rel=src.relative_to(ROOT/f'data/raw/nustar/{OBS}')
        compressed=work/'raw_verified'/rel;copy_verified(src,compressed,x['sha256'])
        dst=work/'input'/rel
        if dst.suffix=='.gz':dst=dst.with_suffix('')
        dst.parent.mkdir(parents=True,exist_ok=True)
        if compressed.suffix=='.gz':
            with gzip.open(compressed,'rb') as fi,dst.open('wb') as fo:shutil.copyfileobj(fi,fo)
        else:shutil.copyfile(compressed,dst)
        return dict(original_path=str(src),raw_sha256=x['sha256'],staged_path=str(dst.relative_to(work)),sha256=sha(dst))
    with concurrent.futures.ThreadPoolExecutor(4) as pool:records=list(pool.map(stage,manifest))
    (work/'staged_inputs.json').write_text(json.dumps(records,indent=2)+'\n')
    args=['nupipeline','indir=input',f'steminputs=nu{OBS}','outdir=clean','instrument=ALL','obsmode=SCIENCE','entrystage=1','exitstage=2','saamode=OPTIMIZED','saacalc=3','tentacle=yes',f'statusexpr={EXPR}','clobber=no','history=yes']
    env=os.environ.copy();env['PHASE2_PFILES']=str(work/'pfiles')
    rec=dict(obsid=OBS,argv=args,physical_cwd=str(work),started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='Locked any corrected one-second bin above 100 count/s trigger; official FAQ spectroscopy shield veto retained',official_guidance='https://heasarc.gsfc.nasa.gov/docs/nustar/nustar_faq.html',retained_directory=str(saved))
    (work/'command.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('Starting genuine level-1 rerun',flush=True)
    with (work/'nupipeline.log').open('w') as log:
        p=subprocess.run(['bash','-c','source "$1"; shift; exec "$@"','x1',str(ROOT/'configs/nustar_env.sh'),*args],cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    rec.update(exit_code=p.returncode,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (work/'command.json').write_text(json.dumps(rec,indent=2)+'\n')
    # The original compressed archive and verified staging manifest retain L1 provenance.
    # Avoid duplicating gigabytes of temporary calibrated L1 intermediates.
    saved.mkdir()
    for name in ['command.json','staged_inputs.json','nupipeline.log']:shutil.copyfile(work/name,saved/name)
    for name in ['clean','pfiles']:
        if (work/name).exists():shutil.copytree(work/name,saved/name)
    print('Bright pipeline exit',p.returncode,flush=True)
    if p.returncode:raise RuntimeError('nupipeline failed; see preserved log')
if __name__=='__main__':main()
