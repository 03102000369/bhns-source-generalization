from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from evidence import retrieve, ROOT

DOCS = {
 'numaster.html': 'https://heasarc.gsfc.nasa.gov/W3Browse/nustar/numaster.html',
 'analysis.html': 'https://heasarc.gsfc.nasa.gov/docs/nustar/analysis/',
 'nupipeline.html': 'https://heasarc.gsfc.nasa.gov/docs/software/lheasoft/help/nupipeline.html',
 'nuproducts.html': 'https://heasarc.gsfc.nasa.gov/docs/software/lheasoft/help/nuproducts.html',
 'nustar_caldb.html': 'https://heasarc.gsfc.nasa.gov/docs/heasarc/caldb/nustar/',
 'nustar_swguide.pdf': 'https://heasarc.gsfc.nasa.gov/docs/nustar/analysis/nustar_swguide.pdf',
 'nustar_quickstart.pdf': 'https://heasarc.gsfc.nasa.gov/docs/nustar/analysis/nustar_quickstart_guide.pdf',
 'minbar_sources.html': 'https://burst.sci.monash.edu/sources',
}

def get(item):
    name, url = item
    return retrieve(url, 'data/reference/evidence/' + name)

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        for rec in pool.map(get, DOCS.items()):
            print(rec['path'], rec['bytes'], flush=True)
    query = 'SELECT * FROM numaster ORDER BY obsid'
    url = 'https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync?' + urlencode(dict(REQUEST='doQuery', LANG='ADQL', FORMAT='text/plain', QUERY=query, MAXREC=100000))
    rec = retrieve(url, 'data/reference/evidence/numaster_all.txt')
    print(rec['path'], rec['bytes'], flush=True)
