"""New exposure maps for the bright-screened coordinate realization."""
from pathlib import Path
from paths import scratch_root, calibration_root
import concurrent.futures,datetime,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];LOCAL=scratch_root()/'30363002002'
def run(m):
    clean=LOCAL/'bright_attempt001/clean';work=LOCAL/m/'exposure_bright';saved=ROOT/f'data/processed/nustar/30363002002/x1_{m}/exposure_bright'
    if work.exists() or saved.exists():raise ValueError('Attempt exists')
    work.mkdir()
    args=['nuexpomap',f'infile={clean}/nu30363002002{m}01_cl.evt',f'mastaspectfile={clean}/nu30363002002_mast.fits',f'attfile={clean}/nu30363002002_att.fits',f'det1reffile={clean}/nu30363002002{m}_det1.fits','expomapfile=exposure.img','det1instrfile=det1_maps.fits','aspecthistofile=aspect_hist.fits','offsetfile=offset.fits','vignflag=no','initseed=yes','pixbin=5','clobber=no','history=yes']
    env=os.environ.copy();env['PHASE2_PFILES']=str(work/'pfiles')
    rec=dict(argv=args,started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),physical_cwd=str(work))
    with (work/'task.log').open('w') as log:p=subprocess.run(['bash','-c','source "$1"; shift; exec "$@"','x1',str(ROOT/'configs/nustar_env.sh'),*args],cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    rec.update(exit_code=p.returncode,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(work/'command.json').write_text(json.dumps(rec,indent=2)+'\n');shutil.copytree(work,saved);print(m,p.returncode,flush=True)
    if p.returncode:raise ValueError('Exposure map failed')
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:list(pool.map(run,'AB'))
