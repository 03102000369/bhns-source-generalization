"""Immutable public evidence retrieval for Phase II only."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    # Read original bytes only. A fresh native reader can resolve transient
    # macOS per-handle timeouts; a persistent failure still raises.
    path=Path(path)
    try:
        size=path.stat().st_size
        if size <= 16*1024*1024:
            data=path.read_bytes()
            if len(data)!=size:raise TimeoutError('Incomplete filesystem read')
            return hashlib.sha256(data).hexdigest()
        digest=hashlib.sha256()
        read=0
        with path.open('rb') as f:
            while chunk:=f.read(1024*1024):
                digest.update(chunk);read+=len(chunk)
        if read!=size:raise TimeoutError('Incomplete filesystem read')
        return digest.hexdigest()
    except TimeoutError:
        import subprocess
        result=subprocess.run(['shasum','-a','256',str(path)],check=True,
                              capture_output=True,text=True,timeout=60)
        value=result.stdout.split()[0]
        if len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Invalid native SHA-256 output')
        if path.stat().st_size>0 and value==hashlib.sha256(b'').hexdigest():
            raise TimeoutError('Native reader returned empty bytes for nonempty file')
        return value

def retrieve(url, relative_path, timeout=90):
    path = ROOT / relative_path
    path.resolve().relative_to(ROOT.resolve())
    meta = path.with_name(path.name + '.retrieval.json')
    if path.exists() and meta.exists():
        rec = json.loads(meta.read_text())
        if rec['url'] != url or rec['sha256'] != sha256(path):
            raise ValueError('Existing evidence differs: ' + str(path))
        return rec
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique staging paths prevent two retrievals sharing a writable inode.
    part = path.with_name(path.name + f'.{os.getpid()}.partial')
    rec = dict(url=url, path=str(path.relative_to(ROOT)), retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        with urlopen(Request(url, headers={'User-Agent': 'BHNS-cross-mission-research/1.0'}), timeout=timeout) as response, part.open('wb') as out:
            rec['response_url'] = response.url
            rec['headers'] = dict(response.headers)
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        os.replace(part, path)
        rec.update(status='RETRIEVED', bytes=path.stat().st_size, sha256=sha256(path))
        meta.write_text(json.dumps(rec, indent=2) + '\n')
        return rec
    except Exception as exc:
        rec.update(status='FAILED', error=repr(exc))
        path.with_name(path.name + '.failure.json').write_text(json.dumps(rec, indent=2) + '\n')
        raise

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('url'); p.add_argument('path')
    a = p.parse_args()
    print(json.dumps(retrieve(a.url, a.path), indent=2))
