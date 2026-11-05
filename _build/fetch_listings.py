#!/usr/bin/env python3
"""Refresh the rental listings from Hostflow.

    python3 _build/fetch_listings.py && python3 _build/build.py

Downloads the public listings feed (the same data as James's Hostflow listings page) into
_build/listings.json and each cover photo into assets/listings/<photo-id>.webp (800px wide).
Hostflow serves its photos for its own domain only, so the site keeps its own copies.
Photos already downloaded are kept; photos no longer used are deleted.
Needs `cwebp` (brew install webp).
"""
import datetime, json, os, shutil, subprocess, sys, tempfile, urllib.request

TOKEN = 'fv0tM03REiayJ2NegmXX-5RK'
API = f'https://hostflow.in/api/v1/public-listings/{TOKEN}'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PHOTOS = os.path.join(ROOT, 'assets', 'listings')


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'medellinconcierge.net site build'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


if not shutil.which('cwebp'):
    sys.exit('cwebp not found: brew install webp')

data = json.loads(get(API))
props = data.get('properties')
if not isinstance(props, list) or not props:
    sys.exit('Hostflow returned no properties; keeping the previous listings.json')
data['fetched'] = datetime.date.today().isoformat()

os.makedirs(PHOTOS, exist_ok=True)
wanted = set()
for p in props:
    pid = p.get('cover_photo')
    if not pid:
        continue
    wanted.add(pid + '.webp')
    out = os.path.join(PHOTOS, pid + '.webp')
    if os.path.exists(out):
        continue
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(get(f'{API}/photos/{pid}')); src = f.name
    r = subprocess.run(['cwebp', '-quiet', '-q', '72', '-resize', '800', '0', src, '-o', out])
    os.unlink(src)
    if r.returncode:
        sys.exit(f'cwebp failed on photo {pid} ({p.get("ref")})')
    print('  photo', p.get('ref'), pid)

for f in os.listdir(PHOTOS):
    if f.endswith('.webp') and f not in wanted:
        os.unlink(os.path.join(PHOTOS, f)); print('  removed old photo', f)

json.dump(data, open(os.path.join(HERE, 'listings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
active = sum(1 for p in props if p.get('active'))
print(f'{len(props)} properties ({active} active) saved to _build/listings.json')
