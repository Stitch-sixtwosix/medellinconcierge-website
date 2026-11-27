# Official COP/USD rate (TRM, Tasa Representativa del Mercado) for the approximate US-dollar figures next to
# listing prices on the English rental pages. Source: Superintendencia Financiera de Colombia, published as open
# data on datos.gov.co (dataset 32sa-8pi3). Refreshed at most once a week, so pages don't change every day just
# because the rate moved; the date of the rate is printed next to the figures. If the source can't be reached,
# the last copy in trm_cache.json is used; with no copy at all, no dollar figures are shown.
import datetime, json, os, urllib.request

API = 'https://www.datos.gov.co/resource/32sa-8pi3.json?$order=vigenciadesde%20DESC&$limit=1'
SOURCE_URL = 'https://www.datos.gov.co/d/32sa-8pi3'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trm_cache.json')
MAX_AGE_DAYS = 7


def _cached():
    try:
        d = json.load(open(CACHE, encoding='utf-8'))
        return d if d.get('date') and d.get('value') else None
    except (OSError, ValueError):
        return None


def load_trm():
    """{'date': 'YYYY-MM-DD', 'value': float COP per USD} or None."""
    old = _cached()
    today = datetime.date.today()
    if old and (today - datetime.date.fromisoformat(old['date'])).days < MAX_AGE_DAYS:
        return old
    try:
        req = urllib.request.Request(API, headers={'User-Agent': 'medellinconcierge.net site build'})
        row = json.load(urllib.request.urlopen(req, timeout=20))[0]
        new = {'date': row['vigenciadesde'][:10], 'value': round(float(row['valor']), 2)}
        if not 1000 < new['value'] < 10000:
            raise ValueError('implausible TRM')
    except Exception as e:   # network blocked, timeout or format change: keep the last good copy
        print(f'  note: TRM not reachable ({type(e).__name__}); using trm_cache.json from {old and old["date"]}')
        return old
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(new, f, indent=1)
    return new


def usd(cop_amount, trm):
    """Approximate US dollars, rounded to the nearest 10 (nearest 1 under US$200), formatted 'US$1,930'."""
    x = cop_amount / trm['value']
    x = round(x, -1) if x >= 200 else round(x)
    return f'US${int(x):,}'
