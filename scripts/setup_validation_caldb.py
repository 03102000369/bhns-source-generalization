"""Install the dated PCA CALDB package into a separate short-path local store."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json,subprocess,time,os

ROOT=Path(__file__).resolve().parents[1]
DEST=Path(os.environ['CALDB']).expanduser().resolve()
BASE='https://heasarc.gsfc.nasa.gov/FTP/caldb/'
FILES={
 'pca_20230501.tar.Z': BASE+'data/xte/pca/goodfiles_xte_pca_20230501.tar.Z',
 'software/tools/caldb.config':BASE+'software/tools/caldb.config',
 'software/tools/alias_config.fits':BASE+'software/tools/alias_config.fits',
}

def main():
    records=[]
    for name,url in FILES.items():
        path=DEST/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            for attempt in range(3):
                try:
                    with urlopen(url,timeout=120) as r, path.with_suffix(path.suffix+'.part').open('wb') as f:
                        while chunk:=r.read(1024*1024):f.write(chunk)
                    path.with_suffix(path.suffix+'.part').replace(path);break
                except Exception:
                    if attempt==2:raise
                    time.sleep(1)
        records.append(dict(url=url,path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if name.endswith('.tar.Z'):
            names=subprocess.check_output(['tar','-tf',str(path)],text=True).splitlines()
            if any(Path(n).is_absolute() or '..' in Path(n).parts for n in names):raise ValueError('Unsafe archive path')
            subprocess.run(['tar','-xf',str(path),'-C',str(DEST)],check=True)
    (ROOT/'results/validation_heasoft/caldb_installation.json').write_text(json.dumps(dict(root=str(DEST),release='20230501',downloads=records,files={str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (DEST/'data').rglob('*') if p.is_file()}),indent=2))
    print('Installed CALDB:',DEST,flush=True)

if __name__=='__main__':main()
