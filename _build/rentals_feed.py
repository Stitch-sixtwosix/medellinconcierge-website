# Live rental listings for /rentals/ and /es/arriendos/: read at build time from HostFlow's public listings feed
# (the same data the embedded listings page shows), so the page carries a crawlable list of what is available.
#
# The feed is public (it is what the embed loads in every visitor's browser). Only bookable properties
# ("active": shown with a price and "I'm interested" in the embed) are listed; the rest are "on request".
# If hostflow.in can't be reached (e.g. a cloud session without access), the last copy in listings_cache.json is
# used, so the build never fails on it. "as_of" is the day the data last changed, shown on the page next to prices.
import datetime, json, os, urllib.request

FEED = 'https://hostflow.in/api/v1/public-listings/fv0tM03REiayJ2NegmXX-5RK'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'listings_cache.json')
KEEP = ('ref', 'title_en', 'title_es', 'area', 'property_type', 'bedrooms', 'bathrooms', 'max_guests',
        'stay_type', 'price', 'cleaning_fee', 'available_from', 'amenities')


def _cached():
    try:
        return json.load(open(CACHE, encoding='utf-8'))
    except (OSError, ValueError):
        return {'as_of': None, 'total': 0, 'properties': []}


def load_listings():
    """{'as_of': 'YYYY-MM-DD', 'total': all properties incl. on request, 'properties': [bookable ones]}"""
    old = _cached()
    try:
        req = urllib.request.Request(FEED, headers={'User-Agent': 'medellinconcierge.net site build'})
        data = json.load(urllib.request.urlopen(req, timeout=20))
        allp = data['properties']
        props = [{k: p.get(k) for k in KEEP} for p in allp if p.get('active') and p.get('stay_type') in ('long_term', 'short_term')]
    except Exception as e:   # network blocked, timeout, or format change: keep the last good copy
        print(f'  note: HostFlow listings feed not reachable ({type(e).__name__}); using listings_cache.json from {old["as_of"]}')
        return old
    new = {'total': len(allp), 'properties': props}
    if new['properties'] == old['properties'] and new['total'] == old['total']:
        return old
    new = {'as_of': datetime.date.today().isoformat(), **new}
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    return new
