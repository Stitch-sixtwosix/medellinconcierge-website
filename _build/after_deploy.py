#!/usr/bin/env python3
"""Run after every publish, once GitHub Pages has finished deploying:

    python3 _build/after_deploy.py              # check the live site, notify search engines of pages changed today
    python3 _build/after_deploy.py 2026-11-01   # ... of pages changed since that date
    python3 _build/after_deploy.py --all        # ... of every page in the sitemap

1. Checks that the live site can be indexed: robots.txt allows crawling and names the sitemap, and every page in
   the live sitemap answers 200, has no "noindex", has a canonical pointing to itself and its EN/ES hreflang pair.
   Any problem is printed and the script exits with status 1 before notifying anyone.
2. Sends the changed pages (sitemap <lastmod> on or after the date) to IndexNow, which passes them to Bing,
   Yandex, Seznam, Naver and the other IndexNow engines.

Google does not accept pings (its sitemap ping was retired in 2023). It rereads sitemap.xml, which is listed in
robots.txt and in Search Console, and uses <lastmod> to decide what to recrawl, so accurate dates are what matter.
"""
import datetime, json, re, sys, time, urllib.error, urllib.request, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_config import SITE, INDEXNOW_KEY

UA = {'User-Agent': 'MedellinConcierge-site-check/1.0'}
HOST = SITE.split('/')[2]


def get(url):
    req = urllib.request.Request(f'{url}{"&" if "?" in url else "?"}nocache={int(time.time())}', headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''


problems = []
status, robots = get(SITE + 'robots.txt')
if status != 200 or f'Sitemap: {SITE}sitemap.xml' not in robots or re.search(r'^Disallow:\s*/\s*$', robots, re.M):
    problems.append('robots.txt is missing, blocks the site or does not list the sitemap')

status, sitemap = get(SITE + 'sitemap.xml')
entries = re.findall(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', sitemap)
if status != 200 or not entries:
    sys.exit('sitemap.xml could not be read on the live site')

for url, _ in entries:
    status, h = get(url)
    if status != 200:
        problems.append(f'{url}: HTTP {status}'); continue
    if re.search(r'<meta name="robots" content="[^"]*noindex', h):
        problems.append(f'{url}: marked noindex but listed in the sitemap')
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', h)
    if not canon or canon.group(1) != url:
        problems.append(f'{url}: canonical is {canon.group(1) if canon else "missing"}')
    for lang in ('en', 'es', 'x-default'):
        if f'hreflang="{lang}"' not in h:
            problems.append(f'{url}: hreflang {lang} missing')

print(f'Checked robots.txt and {len(entries)} pages in the live sitemap.')
if problems:
    print('PROBLEMS, search engines were not notified:'); [print('  -', p) for p in problems]
    sys.exit(1)
print('All pages can be indexed.')

arg = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
changed = [u for u, d in entries if arg == '--all' or d >= arg]
if not changed:
    print(f'No pages changed since {arg}; nothing to send to IndexNow.'); sys.exit(0)

status, key = get(f'{SITE}{INDEXNOW_KEY}.txt')
if status != 200 or key.strip() != INDEXNOW_KEY:
    sys.exit(f'IndexNow key file {SITE}{INDEXNOW_KEY}.txt is not live yet; publish it first.')

body = json.dumps({'host': HOST, 'key': INDEXNOW_KEY, 'keyLocation': f'{SITE}{INDEXNOW_KEY}.txt',
                   'urlList': changed}).encode()
req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body, method='POST',
                             headers={**UA, 'Content-Type': 'application/json; charset=utf-8'})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f'IndexNow accepted {len(changed)} URL(s) (HTTP {r.status}):')
except urllib.error.HTTPError as e:
    sys.exit(f'IndexNow refused the request: HTTP {e.code} {e.read().decode()[:200]}')
for u in changed:
    print('  ', u)
