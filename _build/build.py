#!/usr/bin/env python3
"""Build medellinconcierge.net (static site, no dependencies).

    python3 _build/build.py

index.html (English home page) is the hand-edited source. This script then:
  1. refreshes index.html: latest blog cards + structured data (business, website, FAQ)
  2. writes es/index.html from index.html + the Spanish strings in es_home.py
  3. writes the blog in both languages from _build/posts/*.json (one file per post)
  4. writes the area / foreign-owner landing pages from landing.py, and the rental listings
     pages (/rentals/, /es/arriendos/) that embed the live Hostflow listings
  5. writes sitemap.xml and robots.txt
It stops with a clear message if an English string in es_home.py no longer exists in index.html.
"""
import datetime, glob, hashlib, html, json, os, re, subprocess, sys, unicodedata, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from es_home import HOME_ES, BLOG_UI
from site_config import SITE, BUSINESS, SAME_AS, NEWSLETTER_ENDPOINT
from landing import PAGES, AREAS
from team import TEAM
from faq import FAQ
from fees import FEES
from calculator import CALC
from diamond_card import VENUES, DIAMOND, SINMENTE_SIGNUP
from rentals_feed import load_listings

TODAY = datetime.date.today().isoformat()
LANGS = ('en', 'es')
ARROW = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
CHECK = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10"/></svg>'
MONTHS = {'en': 'January February March April May June July August September October November December'.split(),
          'es': 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()}
SITEMAP = []   # (en_url, es_url, lastmod) for every indexable page pair


def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

# Cache busting: every page links site.css / nav.js as "?v=<fingerprint of the file>", so after a style or script
# change browsers fetch the new file at once instead of using a cached copy for up to 10 minutes (GitHub Pages).
ASSET_V = {f: hashlib.sha1(open(os.path.join(ROOT, 'assets', f), 'rb').read()).hexdigest()[:8] for f in ('site.css', 'nav.js')}
def stamp(s):
    return re.sub(r'assets/(site\.css|nav\.js)(?:\?v=[0-9a-f]+)?"', lambda m: f'assets/{m.group(1)}?v={ASSET_V[m.group(1)]}"', s)

def write(p, s):
    if p.endswith('.html'): s = stamp(s)
    full = os.path.join(ROOT, p); os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
    old = open(full, encoding='utf-8').read() if os.path.exists(full) else None
    if old != s:
        open(full, 'w', encoding='utf-8').write(s); print('  wrote', p)

def human_date(iso, lang):
    y, m, d = map(int, iso.split('-'))
    return f'{d} {MONTHS[lang][m-1]} {y}' if lang == 'en' else f'{d} de {MONTHS[lang][m-1]} de {y}'

def jsonld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=1) + '\n</script>'

def strip_tags(h):
    t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))).strip()
    return re.sub(r'\s+([.,;:!?)])', r'\1', re.sub(r'([(])\s+', r'\1', t))


# Google rating line (top of landing and fees pages). Numbers live in site_config.BUSINESS; shown as plain text
# linked to the Google profile, never as AggregateRating schema.
def rating_text(lang):
    r, n, d = BUSINESS['google_rating'], BUSINESS['google_reviews'], BUSINESS['rating_checked']
    if lang == 'es':
        return f'{str(r).replace(".", ",")} de 5 en Google con {n} reseñas ({d.replace("Nov", "nov.")})'
    return f'rated {r} out of 5 on Google from {n} reviews ({d})'
def rating_line(lang):
    r, n = BUSINESS['google_rating'], BUSINESS['google_reviews']
    num = str(r).replace('.', ',') if lang == 'es' else str(r)
    label = (f'<strong>{num}</strong> en Google · {n} reseñas · Ver reseñas' if lang == 'es'
             else f'<strong>{num}</strong> on Google · {n} reviews · Read reviews')
    return (f'<p class="rating-line"><a href="{BUSINESS["map"]}" target="_blank" rel="noopener" '
            f'aria-label="{html.escape(rating_text(lang)[:1].upper() + rating_text(lang)[1:])}"><span class="star" aria-hidden="true">★</span> {label}</a></p>')

# FAQ accordion icon (landing, FAQ and fees pages)
PLUS = '<span class="plus" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg></span>'

# ---------------- landing pages: complete or not ----------------
def lang_complete(c):
    return not (c['description'] is None or c['intro'] is None or any(t is None for _, t in c['blocks']))
COMPLETE = {pg['key']: lang_complete(pg['en']) and lang_complete(pg['es']) for pg in PAGES}
# Where an unfinished page sends visitors instead (home-page section)
PENDING_TARGET = {}   # all unfinished landing pages go to the top of the home page

def set_landing_links(s):
    """Links to landing pages carry data-landing="<key>". Finished pages get their href; unfinished ones lose it
    (CSS hides them, or shows area cards as plain text). Reversible: the source keeps data-landing."""
    slug = {pg['key']: pg['en']['slug'] for pg in PAGES}
    def fix(m):
        attrs = re.sub(r'\s*href="[^"]*"', '', m.group(1))
        key = re.search(r'data-landing="([^"]+)"', attrs).group(1)
        return '<a' + (f' href="{slug[key]}/"' if COMPLETE[key] else '') + attrs + '>'
    return re.sub(r'<a((?:\s+[\w-]+="[^"]*")*?\s+data-landing="[^"]+"(?:\s+[\w-]+="[^"]*")*)>', fix, s)


# ---------------- shared pieces ----------------
def lang_switch(en_href, es_href, current):
    cur = lambda l: ' aria-current="true"' if l == current else ''
    label = 'Idioma' if current == 'es' else 'Language'
    # ES first, matching the switch inside the Hostflow forms and listings
    return (f'<div class="lang-switch" role="group" aria-label="{label}">\n'
            f'      <a href="{es_href}" lang="es" hreflang="es" aria-label="Español"{cur("es")} data-lang="es">ES</a>'
            f'<a href="{en_href}" lang="en" hreflang="en" aria-label="English"{cur("en")} data-lang="en">EN</a>\n    </div>')

def set_switch(s, en_href, es_href, current):
    s, n = re.subn(r'<div class="lang-switch".*?</div>', lambda m: lang_switch(en_href, es_href, current), s, count=1, flags=re.S)
    assert n == 1, 'language switch not found'
    return s

def alternates(en_url, es_url, lang):
    return (f'<link rel="canonical" href="{es_url if lang == "es" else en_url}">\n'
            f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
            f'<link rel="alternate" hreflang="es" href="{es_url}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{en_url}">')

def set_alternates(s, en_url, es_url, lang):
    s, n = re.subn(r'<link rel="canonical"[^>]*>\n<link rel="alternate" hreflang="en"[^>]*>\n<link rel="alternate" hreflang="es"[^>]*>\n<link rel="alternate" hreflang="x-default"[^>]*>',
                   lambda m: alternates(en_url, es_url, lang), s, count=1)
    assert n == 1, 'canonical/hreflang block not found'
    return s

def business_id(): return SITE + '#business'

def provider_ref():
    """Compact business node for Service.provider: crawlers don't join @ids across pages, so repeat the NAP."""
    b = BUSINESS
    return {'@type': ['RealEstateAgent', 'LocalBusiness'], '@id': business_id(), 'name': b['name'], 'url': SITE,
            'telephone': b['telephone'],
            'address': {'@type': 'PostalAddress', 'streetAddress': b['street'], 'addressLocality': b['locality'],
                        'addressRegion': b['region'], 'addressCountry': b['country']}}

def business(lang):
    b = BUSINESS
    services = b['services_es'] if lang == 'es' else b['services_en']
    return {
        '@type': ['RealEstateAgent', 'LocalBusiness'], '@id': business_id(),
        'name': b['name'], 'legalName': b['legal_name'], 'taxID': b['tax_id'],
        'url': SITE + ('es/' if lang == 'es' else ''),
        'logo': SITE + 'assets/logo.png', 'image': SITE + 'assets/mark.png',
        'telephone': b['telephone'], 'email': b['email'],
        'address': {'@type': 'PostalAddress', 'streetAddress': b['street'], 'addressLocality': b['locality'],
                    'addressRegion': b['region'], 'addressCountry': b['country']},
        'geo': {'@type': 'GeoCoordinates', 'latitude': b['lat'], 'longitude': b['lng']},
        'hasMap': b['map'],
        'areaServed': [{'@type': 'Country' if a == 'Colombia' else 'Place', 'name': a} for a in b['area_served']],
        'knowsLanguage': ['en', 'es'],
        'priceRange': b['price_range_es'] if lang == 'es' else b['price_range_en'],
        'knowsAbout': services + ['Registro Nacional de Turismo (RNT)', 'SIRE', 'TRA'],
        'makesOffer': [{'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'serviceType': s, 'areaServed': 'Medellín'}} for s in services],
        'sameAs': SAME_AS,
    }

def faq_schema(page_html):
    qa = re.findall(r'<details><summary>(.*?)<span class="plus".*?</summary><p>(.*?)</p></details>', page_html, flags=re.S)
    assert qa, 'FAQ not found'
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': strip_tags(q),
            'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in qa]}

def set_home_jsonld(s, lang):
    graph = {'@context': 'https://schema.org', '@graph': [
        business(lang),
        {'@type': 'WebSite', '@id': SITE + '#website', 'url': SITE, 'name': BUSINESS['name'],
         'inLanguage': ['en', 'es'], 'publisher': {'@id': business_id()}}]}
    if '<section id="faq">' in s:   # home FAQ block (index.html) → FAQPage, text identical to the visible answers
        graph['@graph'].append(faq_schema(s[s.index('<section id="faq">'):]))
    s, n = re.subn(r'<script type="application/ld\+json">.*?</script>', lambda m: jsonld(graph), s, count=1, flags=re.S)
    assert n == 1, 'JSON-LD block not found in home page'
    return s


# ---------------- posts ----------------
POSTS = []
for f in sorted(glob.glob(os.path.join(HERE, 'posts', '*.json'))):
    p = json.load(open(f, encoding='utf-8'))
    for k in ('slug', 'date', 'en', 'es'):
        assert k in p, f'{os.path.basename(f)} is missing "{k}"'
    for lang in LANGS:
        for k in ('title', 'description', 'minutes', 'body'):
            assert p[lang].get(k), f'{os.path.basename(f)}: "{lang}.{k}" is empty'
    POSTS.append(p)
POSTS.sort(key=lambda p: (p['date'], p['slug']), reverse=True)

def cards(lang, prefix, posts, reveal=True, tag='h3'):
    ui = BLOG_UI[lang]; r = ' reveal' if reveal else ''
    out = ''
    for p in posts:
        t = p[lang]
        out += (f'      <a class="post-card{r}" href="{prefix}{p["slug"]}.html">\n'
                f'        <p class="post-meta"><time datetime="{p["date"]}">{human_date(p["date"], lang)}</time> · {t["minutes"]} {ui["min_read"]}</p>\n'
                f'        <{tag}>{t["title"]}</{tag}>\n'
                f'        <p>{t["description"]}</p>\n'
                f'        <span class="read">{ui["read"]} {ARROW}</span>\n'
                f'      </a>\n')
    return out

# (The home page no longer shows a blog teaser; the blog is linked from the menu and footer.)


# ======================= 1. English home =======================
print('Building…')
en = read('index.html')
# Google rating + review count: one place (site_config.BUSINESS) for every page. The home page hero and the
# reviews block are rewritten from it on each build, so updating the count there updates the whole site (EN + ES).
_gr, _gn = BUSINESS['google_rating'], BUSINESS['google_reviews']
en, _n1 = re.subn(r'<strong>[\d.]+</strong> on Google · \d+ reviews</a>', f'<strong>{_gr}</strong> on Google · {_gn} reviews</a>', en)
en, _n2 = re.subn(r'</svg>\d+ Google reviews</p>', f'</svg>{_gn} Google reviews</p>', en)
assert _n1 == 1 and _n2 == 1, 'index.html: hero rating line or reviews-block count not found; keep "<strong>4.7</strong> on Google · N reviews</a>" and "N Google reviews</p>"'
assert f'<span class="score-num">{_gr}</span>' in en and f'aria-label="{_gr} out of 5 stars"' in en, \
    'index.html reviews block rating does not match google_rating in site_config.py: update score-num and aria-label'
en = set_landing_links(en)
en, _n = re.subn(r'<div class="newsletter" data-newsletter data-endpoint="[^"]*"(?: hidden)?>',
                lambda m: f'<div class="newsletter" data-newsletter data-endpoint="{html.escape(NEWSLETTER_ENDPOINT, quote=True)}"' + ('' if NEWSLETTER_ENDPOINT else ' hidden') + '>', en)
assert _n == 1, 'newsletter block not found in index.html footer'
en = set_home_jsonld(en, 'en')
write('index.html', en)
SITEMAP.append((SITE, SITE + 'es/', TODAY))

# ======================= 2. Spanish home =======================
es = en
missing = [a for a, b in HOME_ES if a not in es]
if missing:
    sys.exit('These English strings in _build/es_home.py are no longer in index.html. Update es_home.py:\n  - '
             + '\n  - '.join(m[:100] for m in missing))
for a, b in HOME_ES:
    es = es.replace(a, b)
es = es.replace(f'href="{FEES["en"]["slug"]}/"', f'href="{FEES["es"]["slug"]}/"')
es = es.replace('href="airbnb-revenue-calculator/"', f'href="{CALC["es"]["slug"]}/"')
es = es.replace('href="short-term-rentals-medellin/"', 'href="apartamentos-por-dias-medellin/"').replace('href="monthly-rentals-medellin/"', 'href="arriendos-por-meses-medellin/"').replace('href="rentals/"', 'href="arriendos/"').replace('href="team/"', 'href="equipo/"').replace('href="faq/"', 'href="preguntas-frecuentes/"').replace('href="commercial/"', 'href="comercial/"')
for pg in PAGES:   # landing page links point to the Spanish versions
    es = es.replace(f'href="{pg["en"]["slug"]}/"', f'href="{pg["es"]["slug"]}/"')
es = set_home_jsonld(es, 'es')
es = re.sub(r"<script>document\.documentElement\.classList\.add\('js'\);.*?</script>",
            "<script>document.documentElement.classList.add('js')</script>", es, count=1, flags=re.S)
es = es.replace(f'<meta property="og:url" content="{SITE}">', f'<meta property="og:url" content="{SITE}es/">')
es = es.replace('assets/share-en.jpg', 'assets/share-es.jpg')
es = set_alternates(es, SITE, SITE + 'es/', 'es')
es = set_switch(es, '../', './', 'es')
es = es.replace('src="assets/', 'src="../assets/').replace('href="assets/', 'href="../assets/')
write('es/index.html', es)

text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', es, flags=re.S)
eng = [t.strip() for t in re.sub(r'<[^>]+>', '\n', text).split('\n')
       if re.search(r"\b(the|and|your|our|we|you|with|for)\b", t.strip()) and len(t.strip()) > 3]
if eng:
    print('  check these lines on es/index.html, they may still be English:'); [print('    ·', t[:90]) for t in eng[:15]]


# ======================= sub-page template =======================
HOME = {'en': en, 'es': es}

def chrome(lang):
    """Header, footer and WhatsApp button from the home page of `lang`, relinked for a page one folder deeper."""
    home = HOME[lang]
    hdr = home[home.index('<header id="top">'):home.index('</header>') + len('</header>')]
    ftr = home[home.index('<footer>'):home.index('</footer>') + len('</footer>')]
    i = home.index('<a class="wa-float"'); wa = home[i:home.index('</a>', i) + 4]
    def rel(h):
        h = h.replace('href="#top"', 'href="../"')
        h = re.sub(r'href="#(?=[a-z])', 'href="../#', h)
        h = re.sub(r'(src|href)="(?!https?:|mailto:|tel:|#|\.\./#|\./"|\.\./"|data:)', lambda m: f'{m.group(1)}="../', h)
        return h
    return rel(hdr), rel(ftr), rel(wa)

def page(lang, *, title, desc, en_url, es_url, en_href, es_href, body, schema, og_type='website', noindex=False):
    assets = '../assets/' if lang == 'en' else '../../assets/'
    hdr, ftr, wa = chrome(lang)
    hdr = set_switch(hdr, en_href, es_href, lang)
    url = es_url if lang == 'es' else en_url
    d = html.escape(desc, quote=True); t = html.escape(title, quote=True)
    robots = '<meta name="robots" content="noindex, follow">\n' if noindex else ''
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
{robots}{alternates(en_url, es_url, lang)}
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{SITE}assets/share-{lang}.jpg">
<meta property="og:image:secure_url" content="{SITE}assets/share-{lang}.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{'Medellín Concierge: administración de propiedades en Medellín' if lang == 'es' else 'Medellín Concierge: property management in Medellín'}">
<meta property="og:site_name" content="Medellín Concierge">
<meta property="og:locale" content="{'es_CO' if lang == 'es' else 'en_US'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}assets/share-{lang}.jpg">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<link rel="icon" type="image/png" href="{assets}favicon.png">
<link rel="apple-touch-icon" href="{assets}apple-touch-icon.png">
<meta name="theme-color" content="#272727">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{assets}site.css">
{jsonld(schema)}
</head>
<body>

{hdr}

<main>
{body}
</main>

{ftr}

{wa}

<script src="{assets}nav.js"></script>
<script>document.getElementById('yr').textContent = new Date().getFullYear();</script>
</body>
</html>
'''

def breadcrumbs(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(items)]}


# Email inquiries for renters (James, Nov 19 2026: "we want more people emailing us for furnished rentals").
# Every rental page keeps its WhatsApp buttons and adds a mailto: path with a prefilled subject and body; the address
# is also shown as plain, selectable text because mailto: links don't open a mail app for everyone.
MAIL = {
 'en': dict(h='Prefer email? Send us your dates, budget and number of guests',
            p='Write to us and our team in El Poblado answers by email, in English or Spanish, with the apartments that fit your stay.',
            btn='Email us about a furnished rental', addr='Or copy our address:', short='Prefer email?',
            listing='Email us about this apartment', wa='Hi! I’m looking for a furnished apartment in Medellín.',
            body='Hi Medellín Concierge,\n\nI am looking for a furnished apartment in Medellín.\n\nDates (arrival – departure): \nNumber of guests: \nBudget (COP per month or per night): \nPreferred area (El Poblado, Laureles, Envigado, other): \n\nThank you,\n',
            body_item='Hi Medellín Concierge,\n\nI am interested in {t} ({ref}).\n\nDates (arrival – departure): \nNumber of guests: \n\nThank you,\n',
            subj={'rentals': 'Furnished rental inquiry', 'monthly': 'Furnished rental inquiry – monthly', 'short': 'Furnished rental inquiry – short stay', 'vacation': 'Vacation rental inquiry – Medellín', 'blog': 'Furnished rental inquiry',
                  'item': 'Furnished rental inquiry – {ref} {t}'}),
 'es': dict(h='¿Prefiere el correo? Envíenos sus fechas, su presupuesto y cuántas personas son',
            p='Escríbanos y nuestro equipo en El Poblado le responde por correo, en español o en inglés, con los apartamentos que se ajustan a su estadía.',
            btn='Escríbanos por correo', addr='O copie nuestro correo:', short='¿Prefiere el correo?',
            listing='Escríbanos por este apartamento', wa='¡Hola! Estoy buscando un apartamento amoblado en Medellín.',
            body='Hola, Medellín Concierge:\n\nEstoy buscando un apartamento amoblado en Medellín.\n\nFechas (llegada – salida): \nNúmero de personas: \nPresupuesto (COP por mes o por noche): \nZona preferida (El Poblado, Laureles, Envigado, otra): \n\nGracias,\n',
            body_item='Hola, Medellín Concierge:\n\nMe interesa {t} ({ref}).\n\nFechas (llegada – salida): \nNúmero de personas: \n\nGracias,\n',
            subj={'rentals': 'Consulta arriendo amoblado', 'monthly': 'Consulta arriendo amoblado – por meses', 'short': 'Consulta arriendo amoblado – por días', 'vacation': 'Consulta alquiler vacacional – Medellín', 'blog': 'Consulta arriendo amoblado',
                  'item': 'Consulta arriendo amoblado – {ref} {t}'}),
}

def mailto(subject, body):
    q = lambda x: urllib.parse.quote(x, safe='')
    return html.escape(f'mailto:{BUSINESS["email"]}?subject={q(subject)}&body={q(body)}')

def mail_href(lang, kind): return mailto(MAIL[lang]['subj'][kind], MAIL[lang]['body'])

def mail_item_href(lang, ref, t):
    m = MAIL[lang]
    return mailto(m['subj']['item'].format(ref=ref, t=t), m['body_item'].format(ref=ref, t=t))

def mail_note(lang, lead=''):
    return f'<p class="mail-note">{lead}{MAIL[lang]["addr"]} <span class="mail-addr">{BUSINESS["email"]}</span></p>'

def mail_block(lang, kind, href=None, wa_text=None):
    """Email box for the body of rental pages and renter blog posts (WhatsApp kept beside it)."""
    m = MAIL[lang]
    wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(wa_text or m['wa'])
    return (f'<aside class="article-cta mail-cta" id="email">\n      <h2>{m["h"]}</h2>\n      <p>{m["p"]}</p>\n'
            f'      <div class="ref-ctas"><a class="btn btn-primary" href="{href or mail_href(lang, kind)}">{m["btn"]}</a>'
            f'<a class="btn btn-outline" href="{wa}" target="_blank" rel="noopener">WhatsApp</a></div>\n'
            f'      {mail_note(lang)}\n    </aside>')

def mail_contact_point():
    return {'@type': 'ContactPoint', 'contactType': 'reservations', 'email': BUSINESS['email'],
            'telephone': BUSINESS['telephone'], 'availableLanguage': ['en', 'es'], 'areaServed': 'CO'}

def mail_publisher():
    """Business node for rental pages' schema, with the reservations ContactPoint (email + WhatsApp)."""
    return dict(provider_ref(), email=BUSINESS['email'], contactPoint=mail_contact_point())


# ======================= 3. Blog =======================
# Service pages a blog post can link to: (href from /blog/ or /es/blog/ minus "../", anchor text, topic keywords).
_pg = {pg['key']: pg for pg in PAGES}
SERVICE_LINKS = {
 'en': [(f"{_pg['airbnb']['en']['slug']}/", 'Airbnb management in Medellín', ['airbnb', 'short-term', 'short stay', 'guests', 'nightly']),
        (f"{_pg['long-term']['en']['slug']}/", 'long-term property management in Medellín', ['long-term', 'long term', '30 nights', 'monthly', 'long stay', 'tenant']),
        (f"{FEES['en']['slug']}/", 'property management fees in Medellín', ['fee', 'how much', 'commission', 'iva']),
        (f"{_pg['colombia']['en']['slug']}/", 'property management in Colombia for foreign owners', ['abroad', 'foreign', 'from overseas', 'non-resident', 'visa']),
        ('rentals/', 'furnished apartments for rent in Medellín', ['furnished', 'fiador', 'where to stay', 'renter', 'nomad', 'month-long'])],
 'es': [(f"{_pg['airbnb']['es']['slug']}/", 'administración de Airbnb en Medellín', ['airbnb', 'renta corta', 'vivienda turística', 'huésped', 'por noches']),
        (f"{_pg['long-term']['es']['slug']}/", 'administración de arriendos y rentas largas en Medellín', ['rentas largas', 'renta larga', 'arriendo', '30 noches', 'por meses', 'arrendatario']),
        (f"{FEES['es']['slug']}/", 'tarifas de administración de propiedades en Medellín', ['tarifa', 'cuánto cobra', 'comisión', 'iva']),
        (f"{_pg['colombia']['es']['slug']}/", 'administración de propiedades en Colombia para propietarios extranjeros', ['exterior', 'extranjer', 'desde afuera', 'no residente', 'visa']),
        ('arriendos/', 'apartamentos amoblados en arriendo en Medellín', ['amoblado', 'fiador', 'dónde quedarse', 'nómada'])],
}

# Posts written for renters get the furnished-rental email box (mail_block) above the owner CTA.
RENTER_POSTS = {'rent-furnished-apartment-medellin-without-fiador', 'where-to-stay-in-medellin-for-a-month', 'medellin-for-remote-workers'}
# Every renter guide (backlog R11) also gets the email box and a "Furnished rentals by area" link row. The row links
# area pages only if they are built this run, so these posts are written after section 4c4 (see RENTER_POST_WRITES).
RENTER_GUIDES = RENTER_POSTS | {'furnished-apartments-for-rent-medellin', 'el-poblado-apartments-for-rent', 'colombia-digital-nomad-visa-medellin',
                                'cost-of-living-medellin'}
RENTER_ROW_MARK = '<!--renter-area-row-->'
RENTER_POST_WRITES = []   # (path, html, lang) written once the rentals pages are known

for lang in LANGS:
    ui = BLOG_UI[lang]
    folder = 'blog' if lang == 'en' else 'es/blog'
    home_url = SITE + ('es/' if lang == 'es' else '')
    blog_url = {'en': SITE + 'blog/', 'es': SITE + 'es/blog/'}
    other = '../es/blog/' if lang == 'en' else '../../blog/'
    sw = lambda slug='': ((f'./{slug}', f'{other}{slug}') if lang == 'en' else (f'{other}{slug}', f'./{slug}'))

    svc_links = '\n'.join(f'      <a href="../{href}">{label[0].upper() + label[1:]}</a>' for href, label, _ in SERVICE_LINKS[lang])
    svc_links += '\n' + '\n'.join(f'      <a href="../{_pg[k][lang]["slug"]}/">{_pg[k][lang]["h1"]}</a>' for k in ('el-poblado', 'laureles', 'envigado', 'sabaneta') if COMPLETE[k])
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["blog"]}</p>
    <h1>{ui["blog_title"]}</h1>
    <p class="lead">{ui["blog_lead"]}</p>
  </div>
</section>
<section class="blog-list">
  <div class="wrap">
    <div class="post-grid">
{cards(lang, '', POSTS, reveal=False, tag='h2')}    </div>
    <nav class="more-posts" aria-label="{ui["svc_h"]}">
      <h2>{ui["svc_h"]}</h2>
      <p>{ui["svc_p"]}</p>
{svc_links}
    </nav>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Blog', 'name': ui['blog_title'], 'url': blog_url[lang], 'inLanguage': lang, 'publisher': {'@id': business_id()},
         'blogPost': [{'@type': 'BlogPosting', 'headline': p[lang]['title'], 'url': blog_url[lang] + p['slug'] + '.html', 'datePublished': p['date']} for p in POSTS]},
        breadcrumbs([(ui['home'], home_url), (ui['blog'], blog_url[lang])])]}
    en_href, es_href = sw()
    write(f'{folder}/index.html', page(lang, title=ui['blog_meta_title'], desc=ui['blog_meta_desc'],
          en_url=blog_url['en'], es_url=blog_url['es'], en_href=en_href, es_href=es_href, body=body, schema=schema))
    if lang == 'en':
        SITEMAP.append((blog_url['en'], blog_url['es'], POSTS[0]['date'] if POSTS else TODAY))

    for p in POSTS:
        t = p[lang]; slug = p['slug'] + '.html'
        others = ''.join(f'<a href="{o["slug"]}.html">{o[lang]["title"]}</a>' for o in POSTS[:6] if o is not p)
        # Each post links to up to 3 service pages that match its topic (unless the post body already links them).
        related = ''
        cands = [(sum(min(t['body'].lower().count(k), 4) + t['title'].lower().count(k) * 6 for k in kws), i, href, label)
                 for i, (href, label, kws) in enumerate(SERVICE_LINKS[lang]) if f'/{href}' not in t['body'] and f'"{href}' not in t['body']]
        picks = [x for x in sorted(cands, key=lambda x: (-x[0], x[1])) if x[0] > 0][:3] or cands[:2]
        if picks:
            related = (f'\n      <p>{"Related services" if lang == "en" else "Servicios relacionados"}: '
                       + ' · '.join(f'<a href="../{href}">{label}</a>' for _, _, href, label in picks) + '</p>')
        is_renter = p['slug'] in RENTER_GUIDES
        renter_mail = ('\n    ' + mail_block(lang, 'blog') + '\n    ' + RENTER_ROW_MARK) if is_renter else ''
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / <a href="./">{ui["blog"]}</a></p>
    <h1>{t["title"]}</h1>
    <p class="post-meta" style="color:var(--on-dark)"><time datetime="{p["date"]}">{human_date(p["date"], lang)}</time> · {t["minutes"]} {ui["min_read"]} · Medellín Concierge</p>
  </div>
</section>
<article class="article">
  <div class="wrap">
    <div class="prose">
{t["body"]}
    </div>{renter_mail}
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas">
        <a class="btn btn-primary" href="../#contact">{ui["cta_1"]}</a>
        <a class="btn btn-outline" href="../#plans">{ui["cta_2"]}</a>
      </div>{related}
    </aside>
    <nav class="more-posts" aria-label="{ui["more_label"]}">
      <h2>{ui["more"]}</h2>
      {others}
    </nav>
  </div>
</article>'''
        url = blog_url[lang] + slug
        schema = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'BlogPosting', 'headline': t['title'], 'description': t['description'], 'inLanguage': lang,
             'datePublished': p['date'], 'dateModified': p.get('modified', p['date']),
             'mainEntityOfPage': url, 'url': url, 'image': SITE + 'assets/mark.png',
             'author': {'@type': 'Organization', 'name': BUSINESS['name'], 'url': SITE},
             'publisher': {'@type': 'Organization', 'name': BUSINESS['name'], '@id': business_id(),
                           'logo': {'@type': 'ImageObject', 'url': SITE + 'assets/logo.png'}}},
            breadcrumbs([(ui['home'], home_url), (ui['blog'], blog_url[lang]), (t['title'], url)])]}
        en_href, es_href = sw(slug)
        post_html = page(lang, title=t.get('seo_title') or f'{t["title"]} | Medellín Concierge', desc=t['description'],
              en_url=blog_url['en'] + slug, es_url=blog_url['es'] + slug, en_href=en_href, es_href=es_href,
              body=body, schema=schema, og_type='article')
        if is_renter: RENTER_POST_WRITES.append((f'{folder}/{slug}', post_html, lang))
        else: write(f'{folder}/{slug}', post_html)
        if lang == 'en':
            SITEMAP.append((blog_url['en'] + slug, blog_url['es'] + slug, p.get('modified', p['date'])))


# ======================= 4. Landing pages =======================
L = {
 'en': dict(home='Home', copy_note='Copy coming: Lupa is drafting this block (James’s office → Keywords). Edit <code>_build/landing.py</code> → <code>{key}</code> → <code>en</code> → <code>{field}</code>.',
            inc_h='What we handle for you', plans_h='Plans and fees', cta_h='Talk to us about your property',
            cta_p='Get a free consultation, an income estimate and a management proposal.', cta_1='Request a free consultation',
            more_h='More from Medellín Concierge', all_plans='Compare plans in detail', faq_h='Frequently asked questions',
            inc=['Listing on Airbnb, Booking.com, Expedia and VRBO, with dynamic pricing and synced calendars',
                 '24/7 guest support, check-ins and check-outs', 'Cleaning and maintenance, coordinated and supervised',
                 'RNT, SIRE and TRA registrations and reporting',
                 'The previous month’s earnings paid within the first 5 business days, with GAAP statements in your owner portal'],
            th=('', 'Long stays (30+ nights)', 'Short stays'), basic='Basic', premium='Premium',
            plans_note='Commissions on rental income, plus IVA. No upfront fees. Premium also pays your property taxes, HOA fees, utilities and internet, with a monthly accounting report.',
            service='Property management'),
 'es': dict(home='Inicio', copy_note='Texto pendiente: Lupa está redactando este bloque (oficina de James → Keywords). Edite <code>_build/landing.py</code> → <code>{key}</code> → <code>es</code> → <code>{field}</code>.',
            inc_h='Lo que gestionamos por usted', plans_h='Planes y tarifas', cta_h='Hablemos de su propiedad',
            cta_p='Solicite una consulta gratuita, una estimación de ingresos y una propuesta de administración.', cta_1='Solicitar una consulta gratuita',
            more_h='Más de Medellín Concierge', all_plans='Comparar los planes en detalle', faq_h='Preguntas frecuentes',
            inc=['Publicación en Airbnb, Booking.com, Expedia y VRBO, con precios dinámicos y calendarios sincronizados',
                 'Atención al huésped 24/7, llegadas y salidas', 'Limpieza y mantenimiento, coordinados y supervisados',
                 'Registros y reportes de RNT, SIRE y TRA',
                 'Las ganancias del mes anterior pagadas dentro de los primeros 5 días hábiles, con estados bajo GAAP en su portal del propietario'],
            th=('', 'Estancias largas (30+ noches)', 'Estancias cortas'), basic='Básico', premium='Premium',
            plans_note='Comisiones sobre los ingresos por renta, más IVA. Sin costos iniciales. Premium además paga su impuesto predial, cuota de administración, servicios públicos e internet, con un reporte contable mensual.',
            service='Administración de propiedades'),
}

def placeholder(lang, key, field, dark=False):
    return f'<div class="placeholder{" on-dark" if dark else ""}">{L[lang]["copy_note"].format(key=key, field=field)}</div>'

for pg in PAGES:
    if not COMPLETE[pg['key']]:
        # Unfinished: never show placeholder copy to visitors. Send them to the matching home-page section.
        for lang in LANGS:
            folder = pg['en']['slug'] if lang == 'en' else 'es/' + pg['es']['slug']
            target = SITE + ('es/' if lang == 'es' else '') + PENDING_TARGET.get(pg['key'], '')
            write(f'{folder}/index.html', f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>Medellín Concierge</title>
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace({json.dumps(target)});</script>
</head>
<body><p><a href="{target}">Medellín Concierge</a></p></body>
</html>
''')
        print(f'  note: {pg["en"]["slug"]}/ copy not finished → redirects to the home page, not linked, not in sitemap')
        continue
    for lang in LANGS:
        c = pg[lang]; ui = L[lang]
        incomplete = False
        intro = f'<div class="lead">{c["intro"]}</div>' if c['intro'] else placeholder(lang, pg['key'], 'intro', dark=True)
        blocks = ''.join(f'\n      <h2>{h}</h2>\n      ' + (b if b else placeholder(lang, pg['key'], f'blocks[{i}]'))
                         for i, (h, b) in enumerate(c['blocks']))
        inc = ''.join(f'<li>{CHECK}{x}</li>' for x in ui['inc'])
        more = ''.join(f'<a href="../{o[lang]["slug"]}/">{o[lang]["h1"]}</a>'
                       for o in PAGES if o is not pg and COMPLETE[o['key']])
        home_href = '../'
        faq = c.get('faq') or []
        faq_html = (f'\n      <h2>{ui["faq_h"]}</h2>\n      <div class="faq">\n'
                    + ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in faq)
                    + '      </div>') if faq else ''
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="{home_href}">{ui["home"]}</a> / {pg["label"][lang]}</p>
    <h1>{c["h1"]}</h1>
    {intro}
    {rating_line(lang)}
  </div>
</section>
<article class="article landing">
  <div class="wrap">
    <div class="prose">{blocks}
      <h2>{ui["inc_h"]}</h2>
      <ul class="landing-checks">{inc}</ul>
      <h2>{ui["plans_h"]}</h2>
      <table>
        <thead><tr><th></th><th>{ui["th"][1]}</th><th>{ui["th"][2]}</th></tr></thead>
        <tbody>
          <tr><th>{ui["basic"]}</th><td>12% + IVA</td><td>17% + IVA</td></tr>
          <tr><th>{ui["premium"]}</th><td>15% + IVA</td><td>20% + IVA</td></tr>
        </tbody>
      </table>
      <p>{ui["plans_note"]} <a href="{home_href}#plans">{ui["all_plans"]}</a></p>{faq_html}
    </div>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas">
        <a class="btn btn-primary" href="{home_href}#contact">{ui["cta_1"]}</a>
        <a class="btn btn-outline" href="https://wa.me/573042773864">WhatsApp</a>
      </div>
    </aside>
    <nav class="more-posts" aria-label="{ui["more_h"]}">
      <h2>{ui["more_h"]}</h2>
      {more}
    </nav>
  </div>
</article>'''
        en_url, es_url = SITE + pg['en']['slug'] + '/', SITE + 'es/' + pg['es']['slug'] + '/'
        home_url = SITE + ('es/' if lang == 'es' else '')
        url = es_url if lang == 'es' else en_url
        schema = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'Service', 'name': c['h1'], 'serviceType': ui['service'], 'url': url, 'inLanguage': lang,
             'provider': provider_ref(),
             'areaServed': {'@type': 'Country' if pg['key'] == 'colombia' else 'Place', 'name': pg['area']}},
            breadcrumbs([(ui['home'], home_url), (pg['label'][lang], url)])]}
        if faq:
            schema['@graph'].insert(1, {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
                {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in faq]})
        if lang == 'en':
            en_href, es_href = './', f'../es/{pg["es"]["slug"]}/'
        else:
            en_href, es_href = f'../../{pg["en"]["slug"]}/', './'
        folder = pg['en']['slug'] if lang == 'en' else 'es/' + pg['es']['slug']
        write(f'{folder}/index.html', page(lang, title=c['title'], desc=c['description'] or c['h1'],
              en_url=en_url, es_url=es_url, en_href=en_href, es_href=es_href, body=body, schema=schema, noindex=incomplete))
        if lang == 'en' and not incomplete and not (pg['es']['description'] is None or pg['es']['intro'] is None or any(b is None for _, b in pg['es']['blocks'])):
            SITEMAP.append((en_url, es_url, TODAY))
        if incomplete:
            print(f'  note: {folder}/ has placeholder copy → noindex, not in sitemap')


# ======================= 4c. Rental listings (/rentals/, /es/arriendos/) =======================
# James's live Hostflow listings page, embedded. It always shows Hostflow's current properties, prices and
# availability. Hostflow picks Spanish or English from the visitor's browser (it has its own EN/ES switch) and
# tells this page its height, so the embed grows to fit without a scrollbar of its own.
HOSTFLOW_LISTINGS = 'https://hostflow.in/listings?t=fv0tM03REiayJ2NegmXX-5RK'
R = {
 'en': dict(slug='rentals', home='Home', crumb='Rentals',
            title='Furnished Apartments for Rent in Medellín | Book Direct',
            desc='Furnished apartments for rent in Medellín: monthly and short-term rentals in El Poblado, Laureles, Envigado and Sabaneta. Live prices; book direct.',
            h1='Furnished apartments for rent in Medellín',
            lead='<strong>Furnished apartments for rent in Medellín, booked direct: Medellín Concierge rents furnished apartments and homes by the month (monthly rentals of 30 nights or more) and by the night (short-term rentals), managed by our local team in El Poblado.</strong> The listings below show live photos, prices and availability from our booking system. Tap “I’m interested” and we’ll answer you on WhatsApp, or email us your dates, in English or Spanish.',
            prose='''
      <h2>How booking direct works</h2>
      <ol><li><strong>Browse the listings.</strong> Photos, prices and availability come live from HostFlow, the platform every property we manage runs on, so what you see is current.</li><li><strong>Email us or tap “I’m interested”.</strong> Send your dates and number of guests to <a href="mailto:sales@medellinconcierge.net?subject=Furnished%20rental%20inquiry">sales@medellinconcierge.net</a>, or tap “I’m interested” on a listing to write on WhatsApp. Either way we answer your questions about the apartment, the building and the area.</li><li><strong>Confirm your stay.</strong> We agree your dates and the details of the stay with you. Our local team, based in El Poblado, coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Monthly rentals in Medellín: furnished apartments by the month</h2>
      <p>Staying a month or more? As of {AS_OF}, {N_MONTH} of our furnished apartments and homes are offered by the month (30 nights or more), from {MIN_MONTH} COP a month, in {MONTH_AREAS}. Each listing shows the monthly price and a one-time cleaning fee; ask us what else is included, such as utilities, internet and cleaning during the stay. See all of them on our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a> page. For a monthly stay, make sure you get a clear written agreement; our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains what to check. Staying several months? See <a href="../blog/colombia-digital-nomad-visa-medellin.html">how long you can stay in Medellín</a>.</p>
      <h2>Short-term rentals in Medellín: furnished apartments by the night</h2>
      <p>For a few nights or a couple of weeks, {N_SHORT} furnished apartments and homes are offered by the night, from {MIN_NIGHT} COP a night; see them all on our <a href="../short-term-rentals-medellin/">short-term rentals in Medellín</a> page. Short stays are tourist rentals: in Colombia they need a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE, which we handle as the property manager (as of November 2026).</p>
      <h2>Apartments for rent in El Poblado, Laureles, Envigado and Sabaneta</h2>
      <ul><li><strong>El Poblado:</strong> the area with the most restaurants, cafés, coworking spaces and nightlife, and an easy first base in the city. See our <a href="el-poblado/">furnished apartments for rent in El Poblado</a>.</li><li><strong>Laureles:</strong> flat, tree-lined and residential, with a local feel and plenty of cafés and parks (<a href="https://medellinguru.com/guide-to-laureles/">Medellin Guru</a>). See our <a href="laureles/">furnished apartments for rent in Laureles</a>.</li><li><strong>Envigado:</strong> a separate municipality just south of Medellín in the Valle de Aburrá (<a href="https://www.lafm.com.co/colombia/envigado-dijo-si-al-area-metropolitana">La FM</a>), quieter and good for everyday life. See our <a href="envigado/">furnished apartments for rent in Envigado</a>.</li><li><strong>Sabaneta:</strong> the smallest municipality in Colombia by area (<a href="https://www.bluradio.com/turismo/el-municipio-mas-pequeno-de-colombia-esta-en-antioquia-y-tiene-planes-imperdibles-so35">Blu Radio</a>), with its own station on Metro Line A (<a href="https://en.wikipedia.org/wiki/Sabaneta_station">Wikipedia</a>). See our <a href="sabaneta/">furnished apartments for rent in Sabaneta</a>.</li></ul>
      <p>The listings above show which areas have availability right now. Not sure which neighborhood fits you? Read <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado for a month-long stay</a>.</p>
      <h2>Renting in Medellín as a foreigner</h2>
      <p><strong>Yes, foreigners can rent an apartment in Medellín.</strong> Colombia’s Constitution (<a href="https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125">Article 100</a>) gives foreigners the same civil rights as Colombians. For newcomers the hard part is usually the paperwork, not the law: for traditional unfurnished leases, many agencies ask for a <em>fiador</em> (a Colombian co-signer), which someone who just arrived rarely has.</p>
      <p>A furnished rental booked directly with the team that manages it is the simpler route for most people arriving from abroad: the apartment is ready to live in, you agree the dates and conditions with us in writing, and we answer in English or Spanish. Requirements depend on the apartment and the length of the stay, so ask us what the one you like needs before you book.</p>
      <ul><li><strong>Short stays:</strong> foreign guests are reported to Migración Colombia through SIRE, which we handle as the property manager (as of November 2026), so have your passport at hand.</li><li><strong>Monthly stays:</strong> get a written agreement with the price, what it includes and the dates. Our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting without a fiador</a> explains the usual alternatives, such as a rental insurance policy or rent paid in advance, and what Ley 820 de 2003 says about deposits.</li><li><strong>Length of stay:</strong> how long you can stay in Colombia depends on your migration status; see <a href="../blog/colombia-digital-nomad-visa-medellin.html">visitor stays and the digital nomad visa</a>.</li></ul>
      <p>This is general information as of November 2026, not legal advice; confirm any contract with a qualified professional.</p>
      <h2>Before you book a furnished apartment in Medellín: a quick checklist</h2>
      <ul><li><strong>For short stays, check the RNT.</strong> Ask for the listing’s RNT number and look it up on the <a href="https://rnt.confecamaras.co/">public RNT system</a>.</li><li><strong>Know the total price.</strong> Ask what the price includes (for example utilities, internet and cleaning) and whether anything is charged on top.</li><li><strong>Agree the dates and rules in writing.</strong> Check-in and check-out times, building rules and, for monthly stays, the length of the agreement.</li><li><strong>Know who to call.</strong> Make sure someone answers 24/7 if something goes wrong during your stay.</li></ul>
      <p>Rules for tourist rentals can change; this reflects how things stand as of November 2026.</p>''',
            faq=[('How do I book a furnished apartment with Medellín Concierge?',
                  'Choose an apartment in the listings on this page and tap “I’m interested”. We answer you on WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) or by email (<a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>), in English or Spanish, and confirm your dates and the details of the stay with you.'),
                 ('Can I ask about an apartment by email instead of WhatsApp?',
                  'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests, your budget and the area you prefer, or use the “Email us about this apartment” button on any listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the total price in writing.'),
                 ('Can foreigners rent an apartment in Medellín?',
                  'Yes. Colombia’s Constitution (Article 100) gives foreigners the same civil rights as Colombians. Traditional unfurnished leases often ask for a Colombian co-signer (fiador), so most newcomers start with a furnished apartment booked directly with the manager, by the month or by the night. Ask us what the apartment you like requires; for short stays we report foreign guests to Migración Colombia through SIRE, so have your passport at hand (as of November 2026; general information, not legal advice).'),
                 ('Are these Medellín apartments for rent by owner?',
                  'No, they are for rent by the manager. Each apartment belongs to a private owner who has hired Medellín Concierge to manage it, in El Poblado, Laureles, Envigado and Sabaneta, and you book directly with our local team instead of through a booking platform. We confirm the price, your dates and what is included in writing, and we are your contact 24/7 during the stay. For stays of a month or more, see our <a href="../monthly-rentals-medellin/">long-term rentals in Medellín</a>, or email <a href="mailto:sales@medellinconcierge.net?subject=Furnished%20rental%20inquiry">sales@medellinconcierge.net</a> with your dates and number of guests.'),
                 ('Can I rent a furnished apartment in Medellín for a month or longer?',
                  'Yes. Our apartments are offered for short stays and for monthly stays of 30 nights or more. The listings show current prices and availability for your dates.'),
                 ('What is included in the price, and is there a cleaning fee?',
                  'Each listing shows its price per month or per night and a one-time cleaning fee; as of {AS_OF}, cleaning fees in our listings run from {MIN_CLEAN} to {MAX_CLEAN} COP. Ask us what else the apartment you like includes, such as utilities, internet and cleaning during the stay, and get it in writing before you pay.'),
                 ('Do I need a fiador (co-signer) or a deposit for a furnished rental in Medellín?',
                  'Not always: a fiador is common for traditional unfurnished leases, and requirements for a furnished rental depend on the apartment and the type of stay, so ask us for the exact conditions of the one you like before you book. For background, our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains the usual alternatives and what <a href="https://normas.cra.gov.co/Gestor/Docs/ley_0820_2003.htm">Ley 820 de 2003</a> says about deposits (as of November 2026; this is general information, not legal advice, so confirm any contract with a qualified professional).'),
                 ('How much does it cost to rent a furnished apartment in Medellín?',
                  'In our listings, as of {AS_OF}, monthly furnished rentals run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the area, the size and the building, plus a one-time cleaning fee. Short stays start from {MIN_NIGHT} COP a night. The listings on this page show the current price of each apartment.'),
                 ('Which neighborhoods are your rentals in?',
                  'As of {AS_OF}, our available furnished rentals are in {AREA_COUNTS}. The listings on this page show which areas have availability right now.'),
                 ('Are the prices and availability up to date?',
                  'Yes. The listings come live from HostFlow, the booking system every property we manage runs on, so they show current photos, prices and availability.'),
                 ('Do you have an RNT for your short-term rentals?',
                  'Short stays in Colombia need a Registro Nacional de Turismo (RNT), and as the property manager we handle RNT, SIRE and TRA for the properties we manage (as of November 2026). Ask us for the RNT number of the apartment you like and check it on the public RNT system.'),
                 ('I own an apartment in Medellín. Can you rent it out like these?',
                  'Yes. We manage apartments for their owners from 12% of rental income + IVA for stays of 30 nights or more and 17% + IVA for short stays, with no upfront fees. See <a href="../airbnb-management-medellin/">Airbnb management in Medellín</a> and <a href="../long-term-property-management-medellin/">long-term property management</a>.')],
            frame_title='Medellín Concierge properties', fallback='Not loading?', fallback_link='Open our listings in a new tab',
            owners_h='Own a property in Medellín?', owners_p='We manage homes like these for their owners, from listing to monthly GAAP statements.',
            owners_cta='See our management plans'),
 'es': dict(slug='es/arriendos', home='Inicio', crumb='Arriendos',
            title='Apartamentos amoblados en arriendo en Medellín | Por meses',
            desc='Apartamentos amoblados en arriendo en Medellín por meses o por noches en El Poblado, Laureles, Envigado y Sabaneta. Precios en vivo; reserve directo.',
            h1='Apartamentos amoblados en arriendo en Medellín',
            lead='<strong>Apartamentos amoblados en arriendo en Medellín, con reserva directa: en Medellín Concierge arrendamos apartamentos y casas amoblados por meses (desde 30 noches) y por noches, administrados por nuestro equipo local en El Poblado.</strong> Las propiedades de abajo muestran fotos, precios y disponibilidad en vivo desde nuestro sistema de reservas. Toque «Me interesa» y le respondemos por WhatsApp, o escríbanos sus fechas por correo, en español o en inglés.',
            prose='''
      <h2>Cómo funciona la reserva directa</h2>
      <ol><li><strong>Mire las propiedades.</strong> Las fotos, los precios y la disponibilidad salen en vivo de HostFlow, la plataforma con la que operamos todas las propiedades que administramos, así que lo que ve está al día.</li><li><strong>Escríbanos por correo o toque «Me interesa».</strong> Envíe sus fechas y cuántas personas son a <a href="mailto:sales@medellinconcierge.net?subject=Consulta%20arriendo%20amoblado">sales@medellinconcierge.net</a>, o toque «Me interesa» en una propiedad para escribirnos por WhatsApp. En ambos casos le resolvemos las dudas sobre el apartamento, el edificio y el sector.</li><li><strong>Confirme su estadía.</strong> Acordamos con usted las fechas y los detalles de la estadía. Nuestro equipo local, con oficina en El Poblado, coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Apartamentos amoblados por meses en Medellín</h2>
      <p>¿Se queda un mes o más? Al {AS_OF}, {N_MONTH} de nuestros apartamentos y casas amoblados se arriendan por meses (desde 30 noches), desde {MIN_MONTH} COP al mes, en {MONTH_AREAS}. Cada propiedad muestra el precio mensual y una tarifa de aseo única; pregúntenos qué más incluye, como servicios públicos, internet y aseo durante la estadía. Véalos todos en nuestra página de <a href="../arriendos-por-meses-medellin/">arriendos por meses en Medellín</a>. Si arrienda por meses, pida siempre un acuerdo claro por escrito; nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica qué revisar. ¿Se queda varios meses? Vea <a href="../blog/colombia-digital-nomad-visa-medellin.html">cuánto tiempo puede quedarse en Medellín</a>.</p>
      <h2>Alquiler de apartamentos en Medellín por noches: estancias cortas</h2>
      <p>Para unas noches o un par de semanas, {N_SHORT} apartamentos y casas amoblados se arriendan por noches, desde {MIN_NIGHT} COP la noche; véalos todos en nuestra página de <a href="../apartamentos-por-dias-medellin/">apartamentos por días en Medellín</a>. La estancia corta es vivienda turística: en Colombia exige el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia por SIRE, algo que nosotros gestionamos como administradores (a noviembre de 2026).</p>
      <h2>Apartamentos en arriendo en El Poblado, Laureles, Envigado y Sabaneta</h2>
      <ul><li><strong>El Poblado:</strong> la zona con más restaurantes, cafés, espacios de coworking y vida nocturna, y una base cómoda para conocer la ciudad. Vea nuestros <a href="el-poblado/">apartamentos amoblados en arriendo en El Poblado</a>.</li><li><strong>Laureles:</strong> plano, arborizado y residencial, con ambiente de barrio y muchos cafés y parques (<a href="https://medellinguru.com/guide-to-laureles/">Medellin Guru</a>). Vea nuestros <a href="laureles/">apartamentos amoblados en arriendo en Laureles</a>.</li><li><strong>Envigado:</strong> un municipio aparte, al sur de Medellín, en el Valle de Aburrá (<a href="https://www.lafm.com.co/colombia/envigado-dijo-si-al-area-metropolitana">La FM</a>), más tranquilo y bueno para la vida diaria. Vea nuestros <a href="envigado/">apartamentos amoblados en arriendo en Envigado</a>.</li><li><strong>Sabaneta:</strong> el municipio más pequeño de Colombia por extensión (<a href="https://www.bluradio.com/turismo/el-municipio-mas-pequeno-de-colombia-esta-en-antioquia-y-tiene-planes-imperdibles-so35">Blu Radio</a>), con estación propia en la Línea A del Metro (<a href="https://en.wikipedia.org/wiki/Sabaneta_station">Wikipedia</a>). Vea nuestros <a href="sabaneta/">apartamentos amoblados en arriendo en Sabaneta</a>.</li></ul>
      <p>Las propiedades de arriba muestran en qué zonas hay disponibilidad hoy. ¿No sabe qué barrio le conviene? Lea <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado para quedarse un mes</a>.</p>
      <h2>Arrendar en Medellín siendo extranjero</h2>
      <p><strong>Sí, un extranjero puede arrendar un apartamento en Medellín.</strong> La Constitución de Colombia (<a href="https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125">artículo 100</a>) les reconoce a los extranjeros los mismos derechos civiles que a los colombianos. Lo difícil para quien acaba de llegar suelen ser los papeles, no la ley: para un arriendo tradicional sin amoblar, muchas inmobiliarias piden <em>fiador</em> (un codeudor colombiano), y quien recién llega casi nunca lo tiene.</p>
      <p>Un apartamento amoblado que se reserva directo con el equipo que lo administra es el camino más sencillo para la mayoría de quienes llegan del exterior: el apartamento está listo para vivir, las fechas y condiciones quedan por escrito con nosotros y le atendemos en español o en inglés. Los requisitos dependen del apartamento y de la duración de la estadía, así que pregúntenos qué pide el que le guste antes de reservar.</p>
      <ul><li><strong>Por noches:</strong> los huéspedes extranjeros se reportan a Migración Colombia por SIRE, algo que gestionamos como administradores (a noviembre de 2026), así que tenga a mano su pasaporte.</li><li><strong>Por meses:</strong> pida un acuerdo por escrito con el precio, lo que incluye y las fechas. Nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo sin fiador</a> explica las alternativas usuales, como la póliza de arrendamiento o pagar por adelantado, y lo que dice la Ley 820 de 2003 sobre los depósitos.</li><li><strong>Tiempo de estadía:</strong> cuánto puede quedarse en Colombia depende de su situación migratoria; vea <a href="../blog/colombia-digital-nomad-visa-medellin.html">estadías de visitante y la visa de nómada digital</a>.</li></ul>
      <p>Es información general a noviembre de 2026, no asesoría legal; revise cualquier contrato con un profesional calificado.</p>
      <h2>Antes de arrendar un apartamento amoblado en Medellín: lista rápida</h2>
      <ul><li><strong>Si es por noches, verifique el RNT.</strong> Pida el número de RNT del anuncio y consúltelo en el <a href="https://rnt.confecamaras.co/">sistema público del RNT</a>.</li><li><strong>Tenga claro el precio total.</strong> Pregunte qué incluye (por ejemplo servicios públicos, internet y aseo) y si se cobra algo aparte.</li><li><strong>Deje por escrito fechas y reglas.</strong> Horarios de llegada y salida, normas del edificio y, si es por meses, la duración del acuerdo.</li><li><strong>Sepa a quién llamar.</strong> Asegúrese de que alguien responda 24/7 si algo pasa durante su estadía.</li></ul>
      <p>Las normas de la vivienda turística pueden cambiar; esto refleja cómo están las cosas a noviembre de 2026.</p>''',
            faq=[('¿Cómo reservo un apartamento amoblado con Medellín Concierge?',
                  'Escoja un apartamento entre las propiedades de esta página y toque «Me interesa». Le respondemos por WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) o por correo (<a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>), en español o en inglés, y acordamos con usted las fechas y los detalles de la estadía.'),
                 ('¿Puedo preguntar por un apartamento por correo en vez de WhatsApp?',
                  'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son, su presupuesto y la zona que prefiere, o use el botón «Escríbanos por este apartamento» de cualquier propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio total.'),
                 ('¿Un extranjero puede arrendar un apartamento en Medellín?',
                  'Sí. La Constitución de Colombia (artículo 100) les reconoce a los extranjeros los mismos derechos civiles que a los colombianos. El arriendo tradicional sin amoblar suele pedir un fiador colombiano, por eso la mayoría de quienes llegan empiezan con un apartamento amoblado reservado directo con el administrador, por meses o por noches. Pregúntenos qué pide el apartamento que le guste; en las estancias por noches reportamos a los huéspedes extranjeros a Migración Colombia por SIRE, así que tenga a mano su pasaporte (a noviembre de 2026; información general, no asesoría legal).'),
                 ('¿Son apartamentos en arriendo directo con el propietario?',
                  'Son apartamentos en arriendo directo con el administrador. Cada apartamento es de un propietario particular que contrató a Medellín Concierge para administrarlo, en El Poblado, Laureles, Envigado y Sabaneta, y usted reserva directo con nuestro equipo local, sin plataforma de reservas de por medio. Le confirmamos por escrito el precio, las fechas y lo que incluye, y durante la estadía nos encuentra 24/7. Para estadías de un mes o más, vea los <a href="../arriendos-por-meses-medellin/">apartamentos amoblados por meses en Medellín</a>, o escriba a <a href="mailto:sales@medellinconcierge.net?subject=Consulta%20arriendo%20amoblado">sales@medellinconcierge.net</a> con sus fechas y cuántas personas son.'),
                 ('¿Puedo arrendar un apartamento amoblado en Medellín por un mes o más?',
                  'Sí. Nuestros apartamentos se arriendan por noches y por meses, desde 30 noches. Las propiedades muestran los precios y la disponibilidad actuales para sus fechas.'),
                 ('¿Qué incluye el precio y se cobra aseo?',
                  'Cada propiedad muestra su precio por mes o por noche y una tarifa de aseo única; al {AS_OF}, el aseo en nuestras propiedades va desde {MIN_CLEAN} hasta {MAX_CLEAN} COP. Pregúntenos qué más incluye el apartamento que le guste, como servicios públicos, internet y aseo durante la estadía, y pídalo por escrito antes de pagar.'),
                 ('¿Necesito fiador (codeudor) o depósito para un arriendo amoblado en Medellín?',
                  'No siempre: el fiador es común en el arriendo tradicional sin amoblar, y los requisitos de un arriendo amoblado dependen del apartamento y del tipo de estadía, así que pregúntenos las condiciones exactas del que le guste antes de reservar. Como referencia, nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica las alternativas usuales y lo que dice la <a href="https://normas.cra.gov.co/Gestor/Docs/ley_0820_2003.htm">Ley 820 de 2003</a> sobre los depósitos (a noviembre de 2026; es información general, no asesoría legal, así que revise cualquier contrato con un profesional calificado).'),
                 ('¿Cuánto cuesta arrendar un apartamento amoblado en Medellín?',
                  'En nuestras propiedades, al {AS_OF}, los arriendos amoblados por meses van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según la zona, el tamaño y el edificio, más una tarifa de aseo única. Las estancias cortas van desde {MIN_NIGHT} COP la noche. Las propiedades de esta página muestran el precio actual de cada apartamento.'),
                 ('¿En qué barrios están sus arriendos?',
                  'Al {AS_OF}, nuestros arriendos amoblados disponibles están en {AREA_COUNTS}. Las propiedades de esta página muestran en qué zonas hay disponibilidad hoy.'),
                 ('¿Los precios y la disponibilidad están al día?',
                  'Sí. Las propiedades salen en vivo de HostFlow, el sistema de reservas con el que operamos todas las propiedades que administramos, así que muestran fotos, precios y disponibilidad actuales.'),
                 ('¿Sus arriendos por noches tienen RNT?',
                  'La renta corta en Colombia exige el Registro Nacional de Turismo (RNT), y como administradores gestionamos el RNT, el SIRE y la TRA de las propiedades que administramos (a noviembre de 2026). Pídanos el número de RNT del apartamento que le guste y consúltelo en el sistema público del RNT.'),
                 ('Tengo un apartamento en Medellín. ¿Me lo pueden arrendar así?',
                  'Sí. Administramos apartamentos para sus dueños desde el 12% de los ingresos por renta + IVA para estancias de 30 noches o más, y el 17% + IVA para estancias cortas, sin costos iniciales. Vea la <a href="../administracion-de-airbnb-medellin/">administración de Airbnb en Medellín</a> y la <a href="../administracion-de-rentas-largas-medellin/">administración de rentas largas</a>.')],
            frame_title='Propiedades de Medellín Concierge', fallback='¿No carga?', fallback_link='Abra nuestras propiedades en una pestaña nueva',
            owners_h='¿Tiene una propiedad en Medellín?', owners_p='Administramos propiedades como estas para sus dueños, desde la publicación hasta los estados financieros mensuales bajo GAAP.',
            owners_cta='Ver nuestros planes de administración'),
}


# Crawlable list of the bookable listings (from the HostFlow feed, see rentals_feed.py), shown under the guides and
# described in ItemList schema, so search engines see the actual apartments, areas and prices (the embed itself is
# noindex on hostflow.in). Prices are dated "as of" the day the feed last changed.
LISTINGS = load_listings()
RL_UI = {
 'en': dict(h='Furnished rentals available now', month='Monthly rentals (30 nights or more)', short='Short stays (by the night)',
            intro='As of {AS_OF}: {N_AVAIL} furnished apartments and homes with a live price, out of {TOTAL} furnished properties we manage; the others are available on request. Prices are in Colombian pesos. For your dates, use the listings above or ask us about any of these on WhatsApp or by email.',
            per=dict(month='/ month', night='/ night'), frm='from ', on_req='Price on request', now='Available now', avail='Available from {d}',
            ask='Ask about {ref}', wa='Hi! I’m interested in property {ref} ({t}).', clean='+ {c} COP cleaning fee',
            beds=('bedroom', 'bedrooms'), baths=('bath', 'baths'), guests='up to {n} guests', and_=' and ',
            short_more='See every apartment we rent by the night, in all areas, on our <a href="../short-term-rentals-medellin/">short-term rentals in Medellín</a> page.',
            amen=dict(ac='Air conditioning', washer='Washer', dryer='Dryer', elevator='Elevator', parking='Parking', gym='Gym', bbq='BBQ area', playground='Playground')),
 'es': dict(h='Arriendos amoblados disponibles hoy', month='Por meses (30 noches o más)', short='Por noches (estancias cortas)',
            intro='Al {AS_OF}: {N_AVAIL} apartamentos y casas amoblados con precio en vivo, de las {TOTAL} propiedades amobladas que administramos; las demás, bajo consulta. Precios en pesos colombianos. Para sus fechas, use las propiedades de arriba o pregúntenos por cualquiera de estas por WhatsApp o por correo.',
            per=dict(month='/ mes', night='/ noche'), frm='desde ', on_req='Precio bajo consulta', now='Disponible ya', avail='Disponible desde el {d}',
            ask='Preguntar por {ref}', wa='¡Hola! Me interesa la propiedad {ref} ({t}).', clean='+ {c} COP de aseo',
            beds=('habitación', 'habitaciones'), baths=('baño', 'baños'), guests='hasta {n} huéspedes', and_=' y ',
            short_more='Vea todos los apartamentos que arrendamos por días, en todas las zonas, en nuestra página de <a href="../apartamentos-por-dias-medellin/">apartamentos por días en Medellín</a>.',
            amen=dict(ac='Aire acondicionado', washer='Lavadora', dryer='Secadora', elevator='Ascensor', parking='Parqueadero', gym='Gimnasio', bbq='Zona BBQ', playground='Zona infantil')),
}
RL_AREA_FIX = {'Ciudad Del Rio': 'Ciudad del Río', 'Guatape': 'Guatapé', 'Medellin': 'Medellín', 'Bogota': 'Bogotá'}
RL_ANTIOQUIA = {'El Poblado', 'Laureles', 'Envigado', 'Sabaneta', 'Medellín', 'Ciudad del Río', 'Guayabal', 'Barbosa', 'Guatapé', 'Peñol', 'Rionegro'}

def cop(n): return '$' + f'{n:,}'.replace(',', '.')

def rl_area(p): return RL_AREA_FIX.get(p['area'], p['area'])

def rl_title(p, lang):
    t = p['title_es' if lang == 'es' else 'title_en'] or p['title_en']
    for a, b in RL_AREA_FIX.items(): t = t.replace(a, b)
    return t

def rl_join(items, lang):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + RL_UI[lang]['and_'] + items[-1]

def rl_price(p): return (p['price'] or {}).get('amount')

def rl_stats(lang):
    P = LISTINGS['properties']
    month = [rl_price(p) for p in P if p['stay_type'] == 'long_term' and rl_price(p)]
    night = [rl_price(p) for p in P if p['stay_type'] == 'short_term' and rl_price(p)]
    areas = {}
    for p in P: areas[rl_area(p)] = areas.get(rl_area(p), 0) + 1
    month_areas = sorted({rl_area(p) for p in P if p['stay_type'] == 'long_term'}, key=lambda a: (-areas[a], a))
    counts = rl_join([f'{a} ({n})' for a, n in sorted(areas.items(), key=lambda x: (-x[1], x[0]))], lang)
    marea = {}
    for p in P:
        if p['stay_type'] == 'long_term': marea[rl_area(p)] = marea.get(rl_area(p), 0) + 1
    mcounts = rl_join([f'{a} ({n})' for a, n in sorted(marea.items(), key=lambda x: (-x[1], x[0]))], lang) if marea else '—'
    clean = [p['cleaning_fee'] for p in P if p.get('cleaning_fee')]
    return {'{MIN_CLEAN}': cop(min(clean)) if clean else '—', '{MAX_CLEAN}': cop(max(clean)) if clean else '—', '{MONTH_AREA_COUNTS}': mcounts, '{AS_OF}': human_date(LISTINGS['as_of'] or TODAY, lang), '{TOTAL}': str(LISTINGS['total']), '{N_AVAIL}': str(len(P)),
            '{N_MONTH}': str(sum(p['stay_type'] == 'long_term' for p in P)), '{N_SHORT}': str(sum(p['stay_type'] == 'short_term' for p in P)),
            '{MIN_MONTH}': cop(min(month)) if month else '—', '{MAX_MONTH}': cop(max(month)) if month else '—',
            '{MIN_NIGHT}': cop(min(night)) if night else '—', '{MONTH_AREAS}': rl_join(month_areas[:6], lang), '{AREA_COUNTS}': counts}

def fill(t, st):
    for k, v in st.items(): t = t.replace(k, v)
    return t

def rl_item(p, lang):
    u = RL_UI[lang]; ref = p['ref'] or ''; t = rl_title(p, lang)
    meta = [f'{p["bedrooms"]} {u["beds"][p["bedrooms"] != 1]}' if p.get('bedrooms') else '',
            f'{p["bathrooms"]} {u["baths"][p["bathrooms"] != 1]}' if p.get('bathrooms') else '',
            u['guests'].format(n=p['max_guests']) if p.get('max_guests') else '']
    amen = [u['amen'][a] for a in (p.get('amenities') or []) if a in u['amen']]
    pr = p['price'] or {}
    price = (f'{u["frm"] if pr.get("from") else ""}{cop(pr["amount"])} COP <span>{u["per"].get(pr.get("per"), "")}</span>'
             if pr.get('amount') else u['on_req'])
    af = p.get('available_from')
    avail = u['now'] if not af or af <= TODAY else u['avail'].format(d=human_date(af, lang))
    clean = f'<p class="rl-fee">{u["clean"].format(c=cop(p["cleaning_fee"]))}</p>' if p.get('cleaning_fee') else ''
    wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(u['wa'].format(ref=ref, t=t))
    return (f'<li class="rl-item" id="p-{ref.lstrip("#")}"><div class="rl-main"><h4>{html.escape(t)}</h4>'
            f'<p class="rl-meta">{" · ".join(m for m in meta if m)}</p>'
            + (f'<p class="rl-amen">{" · ".join(amen)}</p>' if amen else '') +
            f'</div><div class="rl-side"><p class="rl-price">{price}</p>{clean}<p class="rl-avail">{avail}</p>'
            f'<a class="rl-ask" href="{wa}" target="_blank" rel="noopener">{u["ask"].format(ref=ref)}</a>'
            f'<a class="rl-mail" href="{mail_item_href(lang, ref, t)}">{MAIL[lang]["listing"]}</a></div></li>')

def rl_sort(p):   # available now first, El Poblado first, then by area and price
    return ((p['available_from'] or '') > TODAY, rl_area(p) != 'El Poblado', rl_area(p), rl_price(p) or 10**12)

def rl_section(lang, st, only=None, h=None, intro=None, area=None, short_note=True):
    u = RL_UI[lang]; P = [p for p in LISTINGS['properties'] if not area or rl_area(p) == area]
    if not P: return ''
    out = f'<section class="rl" aria-labelledby="rl-h"><h2 id="rl-h">{h or u["h"]}</h2><p class="rl-intro">{fill(intro or u["intro"], st)}</p>'
    for key, st_type in (('month', 'long_term'), ('short', 'short_term')):
        if only and st_type != only: continue
        grp = sorted((p for p in P if p['stay_type'] == st_type), key=rl_sort)
        if grp: out += (f'<h3>{u[key]}</h3>' if not only else '') + '<ul class="rl-list">' + ''.join(rl_item(p, lang) for p in grp) + '</ul>'
        if grp and st_type == 'short_term' and short_note: out += f'<p class="rl-intro">{u["short_more"]}</p>'
    return out + '</section>'

# Rentals by size (backlog R7): one H2 per bedroom count with at least 2 listings, each a compact list linking to the
# full card in the list below (#p-ref), with the count and price range by month and by night, all from the feed.
RS_UI = {
 'en': dict(jump='Browse by size:', h='{n}-bedroom {kind} for rent in Medellín', apt='apartments', studio='apartments and studios', house='apartments and houses',
            jump_one='{n} bedroom', jump_many='{n} bedrooms',
            intro='As of {AS_OF}, we list {k} furnished {n}-bedroom homes{EXTRA}: {PARTS}. Prices are in Colombian pesos, plus a one-time cleaning fee. Tap a name to see the full listing, or email <a href="mailto:sales@medellinconcierge.net?subject={SUBJ}">sales@medellinconcierge.net</a> with your dates.',
            extra_studio=', {c} of them studios', extra_house=', {c} of them houses',
            month_part='{m} by the month ({RANGE} a month)', night_part='{m} by the night (from {LOW} a night)', req='{m} by the month (price on request)',
            subj='{n}-bedroom furnished rental inquiry', month='Monthly', night='By the night',
            faq_q='Do you have 1-, 2- and 3-bedroom furnished apartments for rent in Medellín?',
            faq_a='Yes. As of {AS_OF}, our furnished rentals include {SIZE_COUNTS}. This page lists them by size, with the monthly and nightly prices for each group; tell us how many bedrooms you need, your dates and your budget at <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> or on WhatsApp.',
            cnt='{c} with {n} {b}', beds=('bedroom', 'bedrooms')),
 'es': dict(jump='Por tamaño:', h='{kind} de {n} {hab} en arriendo en Medellín', apt='Apartamentos', studio='Apartamentos y apartaestudios', house='Apartamentos y casas',
            jump_one='{n} habitación', jump_many='{n} habitaciones',
            intro='Al {AS_OF}, tenemos {k} propiedades amobladas de {n} {hab}{EXTRA}: {PARTS}. Precios en pesos colombianos, más una tarifa de aseo única. Toque un nombre para ver la propiedad completa, o escriba a <a href="mailto:sales@medellinconcierge.net?subject={SUBJ}">sales@medellinconcierge.net</a> con sus fechas.',
            extra_studio=', {c} de ellas apartaestudios', extra_house=', {c} de ellas casas',
            month_part='{m} por meses ({RANGE} al mes)', night_part='{m} por noches (desde {LOW} la noche)', req='{m} por meses (precio bajo consulta)',
            subj='Arriendo amoblado de {n} habitaciones', month='Por meses', night='Por noches',
            faq_q='¿Tienen apartamentos amoblados de 1, 2 y 3 habitaciones en arriendo en Medellín?',
            faq_a='Sí. Al {AS_OF}, nuestros arriendos amoblados incluyen {SIZE_COUNTS}. En esta página están agrupados por tamaño, con los precios por mes y por noche de cada grupo; díganos cuántas habitaciones necesita, sus fechas y su presupuesto en <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> o por WhatsApp.',
            cnt='{c} de {n} {b}', beds=('habitación', 'habitaciones')),
}

def rs_groups():
    g = {}
    for p in LISTINGS['properties']:
        if p.get('bedrooms'): g.setdefault(p['bedrooms'], []).append(p)
    return [(n, g[n]) for n in sorted(g) if len(g[n]) >= 2]

def rs_size_counts(lang):
    u = RS_UI[lang]
    return rl_join([u['cnt'].format(c=len(P), n=n, b=u['beds'][n != 1]) for n, P in rs_groups()], lang)

def rs_jump(lang):
    u = RS_UI[lang]; G = rs_groups()
    if not G: return ''
    links = ' · '.join(f'<a href="#size-{n}">{(u["jump_one"] if n == 1 else u["jump_many"]).format(n=n)}</a>' for n, _ in G)
    return f'<p class="rent-updated">{u["jump"]} {links}</p>'

def rs_section(lang, st):
    u = RS_UI[lang]; ru = RL_UI[lang]; G = rs_groups()
    if not G: return ''
    out = '<section class="rl" id="by-size">'
    for n, P in G:
        studios = sum(p['property_type'] == 'Studio' for p in P); houses = sum(p['property_type'] == 'House' for p in P)
        hab = ru['beds'][n != 1]
        h = u['h'].format(n=n, kind=u['house'] if houses else u['studio'] if studios else u['apt'], hab=hab)
        extra = u['extra_house'].format(c=houses) if houses else u['extra_studio'].format(c=studios) if studios else ''
        parts = []
        for key, typ in (('month', 'long_term'), ('night', 'short_term')):
            grp = [p for p in P if p['stay_type'] == typ]
            if not grp: continue
            pr = sorted(rl_price(p) for p in grp if rl_price(p))
            if not pr: parts.append(u['req'].format(m=len(grp)) if key == 'month' else ''); continue
            if key == 'month':
                rng = f'{cop(pr[0])} COP' if pr[0] == pr[-1] else f'{cop(pr[0])} to {cop(pr[-1])} COP'.replace(' to ', ' a ' if lang == 'es' else ' to ')
                parts.append(u['month_part'].format(m=len(grp), RANGE=rng))
            else:
                parts.append(u['night_part'].format(m=len(grp), LOW=f'{cop(pr[0])} COP'))
        parts = [x for x in parts if x]
        intro = (u['intro'].replace('{AS_OF}', st['{AS_OF}']).replace('{k}', str(len(P))).replace('{n}', str(n)).replace('{hab}', hab)
                 .replace('{EXTRA}', extra).replace('{PARTS}', rl_join(parts, lang))
                 .replace('{SUBJ}', urllib.parse.quote(u['subj'].format(n=n))))
        items = ''
        for p in sorted(P, key=lambda p: (p['stay_type'] != 'long_term', rl_sort(p))):
            pr = p['price'] or {}
            price = (f'{ru["frm"] if pr.get("from") else ""}{cop(pr["amount"])} COP <span>{ru["per"].get(pr.get("per"), "")}</span>' if pr.get('amount') else ru['on_req'])
            meta = [rl_area(p), u['month'] if p['stay_type'] == 'long_term' else u['night'],
                    f'{p["bathrooms"]} {ru["baths"][p["bathrooms"] != 1]}' if p.get('bathrooms') else '',
                    ru['guests'].format(n=p['max_guests']) if p.get('max_guests') else '']
            items += (f'<li class="rl-item"><div class="rl-main"><h4><a href="#p-{(p["ref"] or "").lstrip("#")}">{html.escape(rl_title(p, lang))}</a></h4>'
                      f'<p class="rl-meta">{" · ".join(m for m in meta if m)}</p></div><div class="rl-side"><p class="rl-price">{price}</p></div></li>')
        out += f'<h2 id="size-{n}">{h}</h2><p class="rl-intro">{intro}</p><ul class="rl-list">{items}</ul>'
    return out + '</section>'

# Backlog R8: a listing with a live price becomes an Offer (lease out) whose itemOffered is the apartment, the pattern
# schema.org uses for rooms and rentals (Accommodation has no `offers`). Price, currency and unit (month or night) come
# from the feed; nightly prices are "from" prices, so they go in minPrice. Listings without a price stay a bare
# Apartment/House. Never hard-code prices here.
RL_UNIT = {'month': ('MONTH', 'MON'), 'night': ('NIGHT', 'DAY')}

def rl_offer(p, it):
    pr = p['price'] or {}
    if not pr.get('amount') or pr.get('per') not in RL_UNIT: return None
    text, code = RL_UNIT[pr['per']]
    spec = {'@type': 'UnitPriceSpecification', 'priceCurrency': 'COP', 'unitText': text, 'unitCode': code,
            'referenceQuantity': {'@type': 'QuantitativeValue', 'value': 1, 'unitCode': code}}
    spec['minPrice' if pr.get('from') else 'price'] = pr['amount']
    off = {'@type': 'Offer', 'name': it['name'], 'url': it['url'], 'businessFunction': 'http://purl.org/goodrelations/v1#LeaseOut',
           'price': pr['amount'], 'priceCurrency': 'COP', 'priceSpecification': spec,
           'offeredBy': {'@id': business_id(), 'name': BUSINESS['name']}, 'itemOffered': it}
    af = p.get('available_from')
    if af and af > TODAY: off['availabilityStarts'] = af
    return off

def rl_schema(lang, url, only=None, name=None, area=None):
    P = sorted((p for p in LISTINGS['properties'] if (not only or p['stay_type'] == only) and (not area or rl_area(p) == area)), key=lambda p: (p['stay_type'] != 'long_term', rl_sort(p)))
    items = []
    for i, p in enumerate(P, 1):
        typ = {'Apartment': 'Apartment', 'Condo': 'Apartment', 'Studio': 'Apartment', 'House': 'House'}.get(p['property_type'], 'Accommodation')
        addr = {'@type': 'PostalAddress', 'addressLocality': rl_area(p), 'addressCountry': 'CO'}
        if rl_area(p) in RL_ANTIOQUIA: addr['addressRegion'] = 'Antioquia'
        it = {'@type': typ, 'name': rl_title(p, lang), 'url': url + '#p-' + (p['ref'] or '').lstrip('#'), 'address': addr}
        if p.get('bedrooms'): it['numberOfBedrooms'] = p['bedrooms']
        if p.get('bathrooms'): it['numberOfBathroomsTotal'] = p['bathrooms']
        if p.get('max_guests'): it['occupancy'] = {'@type': 'QuantitativeValue', 'maxValue': p['max_guests']}
        it = rl_offer(p, it) or it
        items.append({'@type': 'ListItem', 'position': i, 'item': it})
    return {'@type': 'ItemList', 'name': name or RL_UI[lang]['h'], 'numberOfItems': len(items), 'itemListElement': items}

for lang in LANGS:
    ui = R[lang]
    st = rl_stats(lang)
    rs_faq = [(RS_UI[lang]['faq_q'], RS_UI[lang]['faq_a'].replace('{SIZE_COUNTS}', rs_size_counts(lang)))] if rs_groups() else []
    ui = dict(ui, prose=fill(ui['prose'], st), faq=[(fill(q, st), fill(a, st)) for q, a in ui['faq'][:7] + rs_faq + ui['faq'][7:]])
    en_url, es_url = SITE + R['en']['slug'] + '/', SITE + R['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    faq_html = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in ui['faq'])
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{ui["lead"]}</div>
    <div class="ref-ctas"><a class="btn btn-primary" href="https://wa.me/573042773864?text={urllib.parse.quote(MAIL[lang]["wa"])}" target="_blank" rel="noopener">WhatsApp</a><a class="btn btn-ghost" href="{mail_href(lang, 'rentals')}">{MAIL[lang]["btn"]}</a></div>
    {mail_note(lang, MAIL[lang]["short"] + " ")}
    {rs_jump(lang)}
  </div>
</section>
<section class="rentals">
  <div class="wrap">
    <div class="listings-embed">
      <iframe id="mc-listings" src="{HOSTFLOW_LISTINGS}" title="{ui["frame_title"]}" loading="lazy" style="width:100%;min-height:900px;border:0;display:block" allow="clipboard-write"></iframe>
    </div>
    <p class="rent-updated">{ui["fallback"]} <a href="{HOSTFLOW_LISTINGS}" target="_blank" rel="noopener">{ui["fallback_link"]}</a></p>
    <div class="prose">{ui["prose"]}
    </div>
    {rs_section(lang, st)}
    {rl_section(lang, st)}
    {mail_block(lang, 'rentals')}
    <div class="prose">
      <h2>{L[lang]["faq_h"]}</h2>
      <div class="faq">
{faq_html}      </div>
    </div>
    <aside class="article-cta">
      <h2>{ui["owners_h"]}</h2>
      <p>{ui["owners_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{ui["owners_cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>
<script>window.addEventListener("message",function(e){{if(!e.data||e.data.type!=="hostflow-listings")return;var f=document.getElementById("mc-listings");if(!f||e.source!==f.contentWindow)return;if(e.data.height)f.style.height=e.data.height+"px";if(e.data.scrollTop)f.scrollIntoView({{behavior:"smooth",block:"start"}});}});</script>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'publisher': mail_publisher()},
        {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in ui['faq']]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])] + ([rl_schema(lang, url)] if LISTINGS['properties'] else [])}
    en_href, es_href = (('./', '../es/arriendos/') if lang == 'en' else ('../../rentals/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'rentals/', SITE + 'es/arriendos/', TODAY))


# ======================= 4c2. Monthly rentals (/monthly-rentals-medellin/, /es/arriendos-por-meses-medellin/) =======================
# Mid-term guests (30+ nights): only the monthly listings from the HostFlow feed, plus a guide for renting by the month.
# Targets "monthly rentals Medellín", "mid-term rentals", "furnished apartment for a month"; /rentals/ stays the page
# for all stays (and links here). Facts only from the feed, the rentals page and our blog guides.
M = {
 'en': dict(slug='monthly-rentals-medellin', home='Home', rentals='Rentals', rentals_url='rentals/', crumb='Monthly rentals',
            title='Monthly Rentals Medellín | Furnished Apartments, 30+ Nights',
            desc='Furnished apartments for rent by the month in Medellín for remote work, relocation and long stays. From {MIN_MONTH} COP a month. Email or WhatsApp us.',
            h1='Monthly furnished apartment rentals in Medellín',
            lead='<strong>Need a furnished apartment in Medellín for a month or more? We rent furnished apartments and homes by the month, from 30 nights, and you book directly with the local team that manages them.</strong> As of {AS_OF}, {N_MONTH} monthly rentals are listed with a price, from {MIN_MONTH} COP a month. Pick one below and ask us on WhatsApp or by email, in English or Spanish.',
            cta_wa='Ask about a monthly rental', wa_text='Hi! I’m looking for a furnished apartment in Medellín by the month.', cta_all='See all rentals with live availability',
            list_h='Monthly rentals available now',
            list_intro='As of {AS_OF}, prices in Colombian pesos per month, plus a one-time cleaning fee. Tap “Ask about” and tell us your dates; for live availability, see <a href="../rentals/">all our furnished rentals</a>.',
            prose="""
      <h2>Mid-term rentals for remote work, relocation and long visits</h2>
      <p>A mid-term rental sits between a few nights on Airbnb and a 12-month lease: a furnished apartment for one month or several, ready to live in from the day you arrive. It suits remote workers and digital nomads, people relocating to Medellín while they look for something permanent, work assignments, and families on a long visit. Each of our monthly listings shows the price per month and a one-time cleaning fee.</p>
      <h2>Why rent by the month directly with us</h2>
      <ul><li><strong>Current prices and availability.</strong> Our listings come live from HostFlow, the booking system every property we manage runs on.</li><li><strong>A local team that knows each apartment.</strong> We manage these apartments ourselves, so we can tell you about the building, the street and what is included before you commit.</li><li><strong>Answers on WhatsApp, in English or Spanish.</strong> Our team is based in El Poblado, and guests can reach us 24/7 during the stay.</li></ul>
      <h2>Long-term rentals in Medellín, direct from the manager</h2>
      <p><strong>Looking for a long-term rental in Medellín direct from the owner? With us you deal directly with the local team that manages each apartment for its owner.</strong> We are not the owners: owners hire Medellín Concierge, a property management company based in El Poblado, to rent out and look after their homes. That means we can confirm the monthly price, your dates and what is included, and we are the people you contact during the stay. You book with us directly, by email or WhatsApp, and agree the stay in writing. As of {AS_OF}, {N_MONTH} furnished apartments are listed by the month, from {MIN_MONTH} to {MAX_MONTH} COP a month, plus a one-time cleaning fee.</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="{LT_MAIL}">Email us about a long-term rental</a></div>
      <h2>Where to rent for a month in Medellín</h2>
      <p>Our monthly apartments are in {MONTH_AREAS}. El Poblado has the most restaurants, cafés and coworking spaces; Laureles is flat, residential and local; Envigado is quieter and good for everyday life. For a side-by-side comparison, read <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado for a month-long stay</a>.</p>
      <h2>How to rent a furnished apartment by the month</h2>
      <ol><li><strong>Choose an apartment</strong> from the list above, or tell us what you need: area, bedrooms and dates.</li><li><strong>Email us or ask on WhatsApp.</strong> Write to <a href="mailto:sales@medellinconcierge.net?subject=Furnished%20rental%20inquiry%20%E2%80%93%20monthly">sales@medellinconcierge.net</a> with your dates, number of guests and budget. We confirm availability and answer your questions about the apartment.</li><li><strong>Agree the stay in writing.</strong> Dates, price, what is included and the house rules.</li><li><strong>Move in.</strong> Our local team coordinates your check-in.</li></ol>
      <h2>Before you sign: a monthly rental checklist</h2>
      <ul><li><strong>Know what the monthly price includes,</strong> for example utilities, internet and cleaning, and whether anything is charged on top.</li><li><strong>Ask what you need to rent.</strong> Many Colombian landlords ask for a <em>fiador</em> (guarantor); our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains the alternatives.</li><li><strong>Check how long you can stay in Colombia.</strong> See <a href="../blog/colombia-digital-nomad-visa-medellin.html">visitor stays and the digital nomad visa</a>.</li><li><strong>Get the agreement in writing,</strong> with the dates and what happens if you want to extend or leave early.</li></ul>""",
            faq=[('How much does a monthly rental in Medellín cost?',
                  'In our listings, as of {AS_OF}, furnished monthly rentals run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the area, the size and the building, plus a one-time cleaning fee. Each listing on this page shows its price.'),
                 ('Can I ask about an apartment by email instead of WhatsApp?',
                  'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests, your budget and the area you prefer, or use the “Email us about this apartment” button on any listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the total price in writing.'),
                 ('Are your long-term rentals rented by the owner?',
                  'No, they are rented by the manager. Each apartment belongs to a private owner who has hired Medellín Concierge to manage it, so you deal directly with our local team: we confirm the monthly price, your dates and what is included in writing, and we are your contact 24/7 during the stay. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your move-in date and how many months you need.'),
                 ('What is the minimum stay for a monthly rental?',
                  '30 nights. Staying less than a month? See our <a href="../short-term-rentals-medellin/">short-term rentals in Medellín</a>, furnished apartments by the night.'),
                 ('Which neighborhoods are your monthly rentals in?',
                  'As of {AS_OF}: {MONTH_AREA_COUNTS}. The list on this page shows the current ones.'),
                 ('Do I need a fiador (guarantor) to rent by the month?',
                  'Ask us what each apartment requires before you book. Our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting without a fiador</a> explains how foreigners usually rent furnished apartments in Medellín.'),
                 ('How do I book a monthly rental?',
                  'Tap “Ask about” on the apartment you like, or message us on WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) with your dates. We confirm availability and agree the details of the stay with you.'),
                 ('How long can I stay in Medellín as a visitor?',
                  'It depends on your nationality and visa. Our guide to <a href="../blog/colombia-digital-nomad-visa-medellin.html">how long you can stay in Medellín</a> covers visitor stays, extensions and the digital nomad visa.')]),
 'es': dict(slug='es/arriendos-por-meses-medellin', home='Inicio', rentals='Arriendos', rentals_url='es/arriendos/', crumb='Arriendos por meses',
            title='Arriendos por meses en Medellín | Apartamentos amoblados',
            desc='Apartamentos amoblados por meses en Medellín para trabajo remoto, traslados y estadías largas. Desde {MIN_MONTH} COP al mes. Escríbanos por correo.',
            h1='Apartamentos amoblados en arriendo por meses en Medellín',
            lead='<strong>¿Necesita un apartamento amoblado en Medellín por un mes o más? Arrendamos apartamentos y casas amoblados por meses, desde 30 noches, y usted reserva directo con el equipo local que los administra.</strong> Al {AS_OF} hay {N_MONTH} arriendos por meses con precio, desde {MIN_MONTH} COP al mes. Escoja uno abajo y pregúntenos por WhatsApp o por correo, en español o en inglés.',
            cta_wa='Preguntar por un arriendo por meses', wa_text='¡Hola! Busco un apartamento amoblado en Medellín por meses.', cta_all='Ver todos los arriendos con disponibilidad en vivo',
            list_h='Arriendos por meses disponibles hoy',
            list_intro='Al {AS_OF}, precios en pesos colombianos por mes, más una tarifa de aseo única. Toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo, vea <a href="../arriendos/">todos nuestros arriendos amoblados</a>.',
            prose="""
      <h2>Arriendos de mediano plazo para trabajo remoto, traslados y visitas largas</h2>
      <p>Un arriendo de mediano plazo está entre unas noches en Airbnb y un contrato de 12 meses: un apartamento amoblado por uno o varios meses, listo para vivir desde el día en que llega. Es ideal para trabajadores remotos y nómadas digitales, para quien se traslada a Medellín mientras busca algo permanente, para asignaciones de trabajo y para familias de visita larga. Cada arriendo por meses muestra el precio mensual y una tarifa de aseo única.</p>
      <h2>Por qué arrendar por meses directo con nosotros</h2>
      <ul><li><strong>Precios y disponibilidad al día.</strong> Nuestras propiedades salen en vivo de HostFlow, el sistema de reservas con el que operamos todas las propiedades que administramos.</li><li><strong>Un equipo local que conoce cada apartamento.</strong> Administramos estos apartamentos nosotros mismos, así que le contamos del edificio, la calle y qué incluye antes de que se comprometa.</li><li><strong>Respuestas por WhatsApp, en español o en inglés.</strong> Nuestro equipo está en El Poblado, y durante la estadía nos encuentra 24/7.</li></ul>
      <h2>Apartamentos amoblados en Medellín, directo con quien los administra</h2>
      <p><strong>¿Busca un apartamento amoblado en Medellín directo con el dueño? Con nosotros trata directamente con el equipo local que administra cada apartamento en nombre de su propietario.</strong> No somos los dueños: los propietarios contratan a Medellín Concierge, empresa de administración de propiedades con sede en El Poblado, para arrendar y cuidar sus inmuebles. Por eso le confirmamos el precio mensual, sus fechas y qué incluye, y somos a quienes usted contacta durante la estadía. Reserva directo con nosotros, por correo o por WhatsApp, y deja la estadía por escrito. Al {AS_OF} hay {N_MONTH} apartamentos amoblados publicados por meses, entre {MIN_MONTH} y {MAX_MONTH} COP al mes, más una tarifa de aseo única.</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="{LT_MAIL}">Escríbanos por un arriendo por meses</a></div>
      <h2>Dónde arrendar por un mes en Medellín</h2>
      <p>Nuestros apartamentos por meses están en {MONTH_AREAS}. El Poblado tiene la mayor oferta de restaurantes, cafés y espacios de coworking; Laureles es plano, residencial y de barrio; Envigado es más tranquilo y bueno para la vida diaria. Para compararlos, lea <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado para quedarse un mes</a>.</p>
      <h2>Cómo arrendar un apartamento amoblado por meses</h2>
      <ol><li><strong>Escoja un apartamento</strong> de la lista de arriba, o díganos qué necesita: zona, habitaciones y fechas.</li><li><strong>Escríbanos por correo o por WhatsApp.</strong> Envíe sus fechas, cuántas personas son y su presupuesto a <a href="mailto:sales@medellinconcierge.net?subject=Consulta%20arriendo%20amoblado%20%E2%80%93%20por%20meses">sales@medellinconcierge.net</a>. Confirmamos la disponibilidad y le resolvemos las dudas sobre el apartamento.</li><li><strong>Deje la estadía por escrito.</strong> Fechas, precio, qué incluye y las normas de la casa.</li><li><strong>Instálese.</strong> Nuestro equipo local coordina su llegada.</li></ol>
      <h2>Antes de firmar: lista para un arriendo por meses</h2>
      <ul><li><strong>Tenga claro qué incluye el precio mensual,</strong> por ejemplo servicios públicos, internet y aseo, y si se cobra algo aparte.</li><li><strong>Pregunte qué necesita para arrendar.</strong> Muchos arrendadores en Colombia piden fiador; nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica las alternativas.</li><li><strong>Revise cuánto tiempo puede quedarse en Colombia.</strong> Vea <a href="../blog/colombia-digital-nomad-visa-medellin.html">estadías de visitante y la visa de nómada digital</a>.</li><li><strong>Deje el acuerdo por escrito,</strong> con las fechas y qué pasa si quiere extender o salir antes.</li></ul>""",
            faq=[('¿Cuánto cuesta un arriendo por meses en Medellín?',
                  'En nuestras propiedades, al {AS_OF}, los arriendos amoblados por meses van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según la zona, el tamaño y el edificio, más una tarifa de aseo única. Cada propiedad de esta página muestra su precio.'),
                 ('¿Puedo preguntar por un apartamento por correo en vez de WhatsApp?',
                  'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son, su presupuesto y la zona que prefiere, o use el botón «Escríbanos por este apartamento» de cualquier propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio total.'),
                 ('¿Sus arriendos por meses son directo con el dueño?',
                  'Son directo con quien los administra. Cada apartamento es de un propietario particular que contrató a Medellín Concierge para administrarlo, así que usted trata directamente con nuestro equipo local: le confirmamos por escrito el precio mensual, sus fechas y qué incluye, y somos su contacto 24/7 durante la estadía. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con su fecha de llegada y cuántos meses necesita.'),
                 ('¿Cuál es la estadía mínima de un arriendo por meses?',
                  '30 noches. ¿Se queda menos de un mes? Vea nuestros <a href="../apartamentos-por-dias-medellin/">apartamentos por días en Medellín</a>, amoblados y por noches.'),
                 ('¿En qué barrios están sus arriendos por meses?',
                  'Al {AS_OF}: {MONTH_AREA_COUNTS}. La lista de esta página muestra los actuales.'),
                 ('¿Necesito fiador para arrendar por meses?',
                  'Pregúntenos qué pide cada apartamento antes de reservar. Nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo sin fiador</a> explica cómo suelen arrendar los extranjeros un apartamento amoblado en Medellín.'),
                 ('¿Cómo reservo un arriendo por meses?',
                  'Toque «Preguntar por» en el apartamento que le guste, o escríbanos por WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) con sus fechas. Confirmamos la disponibilidad y acordamos con usted los detalles de la estadía.'),
                 ('¿Cuánto tiempo puedo quedarme en Medellín como visitante?',
                  'Depende de su nacionalidad y su visa. Nuestra guía sobre <a href="../blog/colombia-digital-nomad-visa-medellin.html">cuánto tiempo puede quedarse en Medellín</a> explica las estadías de visitante, las prórrogas y la visa de nómada digital.')]),
}

# R14 (Nov 25 2026, office report mc-2026-11-25): prefilled long-term email for the 'direct from the manager' section
LT_MAIL = {'en': ('Long-term furnished rental inquiry – Medellín',
                  'Hi Medellín Concierge,\n\nI am looking for a long-term furnished rental in Medellín.\n\nMove-in date: \nHow many months: \nNumber of guests: \nBudget (COP per month): \nPreferred area (El Poblado, Laureles, Envigado, other): \n\nThank you,\n'),
           'es': ('Consulta arriendo amoblado por meses – Medellín',
                  'Hola, Medellín Concierge:\n\nEstoy buscando un apartamento amoblado en Medellín por meses.\n\nFecha de llegada: \nCuántos meses: \nNúmero de personas: \nPresupuesto (COP al mes): \nZona preferida (El Poblado, Laureles, Envigado, otra): \n\nGracias,\n')}

# R16 (Nov 26 2026, office report mc-2026-11-26): price-by-area table on the monthly pages, built ONLY from our own live
# monthly listings (lowest monthly price per area and bedroom count). Bing/Google answer boxes quote competitors' price
# tables for 'monthly rentals medellín'; ours is dated and never a market survey.
MT = {
 'en': dict(h='How much is a furnished monthly rental in Medellín?',
            p='<strong>In our own listings, as of {AS_OF}, a furnished apartment by the month in Medellín starts at {MIN_MONTH} COP a month.</strong> The table shows the lowest monthly price we list in each area for each size, plus a one-time cleaning fee. The price depends on the building, the floor and the season, so each listing above shows its own.',
            area='Area', cols=('1 bedroom', '2 bedrooms', '3+ bedrooms'), frm='from ', none='—', ask='ask us',
            note='Prices in Colombian pesos per month from our own listings on {AS_OF}; they are not a market survey. “—” means we have no monthly listing of that size there right now: <a href="{MAIL}">email us</a> your area, size, dates and budget and we tell you what is coming up.',
            faq_q='How much is a 1-, 2- or 3-bedroom furnished apartment per month in Medellín?',
            faq_a='In our listings, as of {AS_OF}: {BY_SIZE} COP a month, plus a one-time cleaning fee. The price depends on the area, the building and the season; the table on this page shows the lowest price by area and size.',
            by_size='{lbl} from {p}', lbl=('1-bedroom', '2-bedroom', '3-bedroom or larger'),
            subj='Monthly rental price inquiry – Medellín',
            body='Hi Medellín Concierge,\n\nI am looking for a furnished apartment by the month.\n\nArea: \nBedrooms: \nMove-in date: \nHow many months: \nBudget (COP per month): \n\nThank you,\n'),
 'es': dict(h='¿Cuánto cuesta un apartamento amoblado por meses en Medellín?',
            p='<strong>En nuestras propiedades, al {AS_OF}, un apartamento amoblado por meses en Medellín arranca en {MIN_MONTH} COP al mes.</strong> La tabla muestra el precio mensual más bajo que publicamos en cada zona para cada tamaño, más una tarifa de aseo única. El precio depende del edificio, el piso y la temporada, por eso cada propiedad de arriba muestra el suyo.',
            area='Zona', cols=('1 habitación', '2 habitaciones', '3 o más'), frm='desde ', none='—', ask='pregúntenos',
            note='Precios en pesos colombianos al mes, tomados de nuestras propias propiedades el {AS_OF}; no es un estudio de mercado. «—» indica que hoy no tenemos un arriendo por meses de ese tamaño en esa zona: <a href="{MAIL}">escríbanos</a> la zona, el tamaño, sus fechas y su presupuesto y le contamos qué se libera pronto.',
            faq_q='¿Cuánto cuesta al mes un apartamento amoblado de 1, 2 o 3 habitaciones en Medellín?',
            faq_a='En nuestras propiedades, al {AS_OF}: {BY_SIZE} COP al mes, más una tarifa de aseo única. El precio depende de la zona, el edificio y la temporada; la tabla de esta página muestra el precio más bajo por zona y tamaño.',
            by_size='{lbl} desde {p}', lbl=('1 habitación', '2 habitaciones', '3 habitaciones o más'),
            subj='Consulta precio arriendo por meses – Medellín',
            body='Hola, Medellín Concierge:\n\nBusco un apartamento amoblado por meses.\n\nZona: \nHabitaciones: \nFecha de llegada: \nCuántos meses: \nPresupuesto (COP al mes): \n\nGracias,\n'),
}

def mt_groups():
    g = {}
    for p in LISTINGS['properties']:
        if p['stay_type'] != 'long_term' or not rl_price(p) or (p.get('price') or {}).get('per') != 'month' or not p.get('bedrooms'): continue
        col = min(p['bedrooms'], 3) - 1
        g.setdefault(rl_area(p), {}).setdefault(col, []).append(rl_price(p))
    return g

def mt_by_size(lang):
    u = MT[lang]; g = mt_groups(); out = []
    for c in range(3):
        v = [x for a in g.values() for x in a.get(c, [])]
        if v: out.append(u['by_size'].format(lbl=u['lbl'][c], p=cop(min(v))))
    return rl_join(out, lang) if out else ''

def mt_section(lang, st):
    u = MT[lang]; g = mt_groups()
    if len(g) < 2: return ''
    n = lambda a: sum(len(v) for v in g[a].values())
    rows = ''
    for a in sorted(g, key=lambda a: (-n(a), a)):
        cells = ''
        for c in range(3):
            v = g[a].get(c, [])
            txt = u['none'] if not v else (cop(min(v)) if len(v) == 1 else u['frm'] + cop(min(v)))
            cells += f'<td>{txt}</td>'
        rows += f'          <tr><th>{a}</th>{cells}</tr>\n'
    mail = mailto(u['subj'], u['body'])
    head = ''.join(f'<th>{c}</th>' for c in u['cols'])
    return f'''
      <h2>{u["h"]}</h2>
      <p>{fill(u["p"], st)}</p>
      <div class="table-scroll"><table class="price-table">
        <thead><tr><th>{u["area"]}</th>{head}</tr></thead>
        <tbody>
{rows}        </tbody>
      </table></div>
      <p><small>{fill(u["note"], st).replace("{MAIL}", mail)}</small></p>'''

for lang in LANGS:
    ui = M[lang]; st = rl_stats(lang)
    en_url, es_url = SITE + M['en']['slug'] + '/', SITE + M['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    pre = '../' if lang == 'en' else '../../'
    faq = [(fill(q, st), fill(a, st)) for q, a in ui['faq']]
    if mt_by_size(lang): faq.insert(1, (MT[lang]['faq_q'], fill(MT[lang]['faq_a'].replace('{BY_SIZE}', mt_by_size(lang)), st)))
    faq_html = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in faq)
    wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(ui['wa_text'])
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / <a href="{pre}{ui["rentals_url"]}">{ui["rentals"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{fill(ui["lead"], st)}</div>
    <div class="ref-ctas"><a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">{ui["cta_wa"]}</a><a class="btn btn-ghost" href="{mail_href(lang, 'monthly')}">{MAIL[lang]["btn"]}</a><a class="btn btn-ghost" href="{pre}{ui["rentals_url"]}">{ui["cta_all"]}</a></div>
    {mail_note(lang, MAIL[lang]["short"] + " ")}
  </div>
</section>
<section class="rentals rentals-month">
  <div class="wrap">
    {rl_section(lang, st, only='long_term', h=ui['list_h'], intro=ui['list_intro'])}
    {mail_block(lang, 'monthly')}
    <div class="prose">{fill(ui["prose"], st).replace("{LT_MAIL}", mailto(LT_MAIL[lang][0], LT_MAIL[lang][1]))}{mt_section(lang, st)}
      <h2>{L[lang]["faq_h"]}</h2>
      <div class="faq">
{faq_html}      </div>
    </div>
    <aside class="article-cta">
      <h2>{R[lang]["owners_h"]}</h2>
      <p>{R[lang]["owners_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{R[lang]["owners_cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': ui['h1'], 'description': fill(ui['desc'], st), 'url': url, 'inLanguage': lang,
         'publisher': mail_publisher()},
        {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in faq]},
        breadcrumbs([(ui['home'], home_url), (ui['rentals'], SITE + ui['rentals_url']), (ui['crumb'], url)])]
        + ([rl_schema(lang, url, only='long_term', name=ui['list_h'])] if LISTINGS['properties'] else [])}
    en_href, es_href = (('./', '../es/arriendos-por-meses-medellin/') if lang == 'en' else ('../../monthly-rentals-medellin/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=fill(ui['desc'], st), en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'monthly-rentals-medellin/', SITE + 'es/arriendos-por-meses-medellin/', TODAY))


# ======================= 4c3. Rentals by neighborhood (/rentals/<area>/, /es/arriendos/<area>/) =======================
# Backlog R3 (James, Nov 19 2026: more renter emails for furnished rentals). One page per area with at least 2 bookable
# listings in the HostFlow feed: answer-first summary from the feed's own numbers, the area's listings, email +
# WhatsApp CTAs, area facts with cited sources, FAQ + FAQPage/ItemList schema. Pages are one folder deeper than
# /rentals/, so the body is written as if it sat at /rentals/ (EN) or /es/arriendos/ (ES) and every relative link is
# shifted one level at the end (deeper()).
RA = {
 'El Poblado': {
  'slug': 'el-poblado',
  'en': dict(title='Furnished Apartments for Rent in El Poblado, Medellín',
             desc='Furnished apartments for rent in El Poblado, Medellín: {N} listed by the month or by the night, with live prices. Book direct by email or WhatsApp.',
             h1='Furnished apartments for rent in El Poblado',
             crumb='El Poblado',
             lead='<strong>Looking for a furnished apartment for rent in El Poblado, Medellín? As of {AS_OF} we have {N} furnished apartments in El Poblado listed: {N_MONTH} by the month (30 nights or more), from {MIN_MONTH} COP a month, and {N_SHORT} by the night, from {MIN_NIGHT} COP a night.</strong> We manage them ourselves from our office in El Poblado, so you book directly with the local team that looks after them. Ask about any of them on WhatsApp or by email, in English or Spanish.',
             wa_text='Hi! I’m looking for a furnished apartment in El Poblado.',
             mail_subj='Furnished rental inquiry – El Poblado',
             lt_h='Long-term rentals in El Poblado, Medellín (30+ nights)',
             lt_p='{N_MONTH} of the apartments below can be rented long term, by the month (30 nights or more), from {MIN_MONTH} to {MAX_MONTH} COP a month, direct from the team that manages them. Email <a href="{MAIL}">sales@medellinconcierge.net</a> with your move-in date and how many months you need, and we confirm the monthly price in writing. More areas: <a href="../monthly-rentals-medellin/">long-term rentals in Medellín</a>.',
             cta_all='See all rentals in Medellín',
             list_h='Furnished apartments in El Poblado available now',
             list_intro='As of {AS_OF}: {N} furnished apartments in El Poblado. Prices are in Colombian pesos, plus a one-time cleaning fee. Tap “Ask about” and tell us your dates; for live availability and our other areas, see <a href="../rentals/">all our furnished rentals in Medellín</a>.',
             prose='''
      <h2>What El Poblado is like to live in</h2>
      <p>El Poblado is Comuna 14 of Medellín, one of the 16 <em>comunas</em> of the city’s urban area (<a href="https://www.medellin.gov.co/es/conoce-algunos-datos-generales-de-la-ciudad/">Alcaldía de Medellín</a>). It sits on the hillside in the southeast of the city and has the highest concentration of hotels, restaurants, coworking spaces and shopping malls; areas such as Parque Lleras and Provenza are known for their nightlife. For a first stay in Medellín that means almost everything is close, and many businesses are used to serving foreigners.</p>
      <p><strong>Getting around:</strong> Metro Line A has stations at Poblado and Aguacatala along the river at the bottom of the hill (<a href="https://www.elcolombiano.com/medellin/socavacion-metro-medellin-estaciones-cerradas-AD30117052">El Colombiano</a>). Higher up the hill, most people use taxis or ride apps, so ask us how far an apartment is from the places you will go every day.</p>
      <h2>Is El Poblado right for your stay?</h2>
      <ul><li><strong>Good fit if you</strong> want to walk to cafés, gyms and restaurants, are new to Medellín and want services in English nearby, or enjoy going out in the evening.</li><li><strong>Think twice if you</strong> are sensitive to noise (especially near the nightlife streets on weekends), want flat streets for walking or cycling (much of El Poblado is steep), or are on a tight budget: guides consistently describe it as the most expensive area of the city (<a href="https://www.expatexchange.com/article/5474/Living-in-Colombia-Best-Places-to-Live-in-Medellin,-Colombia">Expat Exchange</a>).</li></ul>
      <p>Prefer somewhere quieter or flatter? See <a href="../rentals/">our rentals in Laureles, Envigado and Sabaneta</a>, or compare the areas in <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado for a month-long stay</a>.</p>
      <h2>Monthly or nightly: renting in El Poblado</h2>
      <p><strong>By the month (30 nights or more).</strong> As of {AS_OF}, our {N_MONTH} monthly apartments in El Poblado run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the size and the building, plus a one-time cleaning fee. See every monthly apartment in the city on our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a> page. For a monthly stay, get a clear written agreement; our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains what to check.</p>
      <p><strong>By the night.</strong> For a few nights or a couple of weeks, {N_SHORT} El Poblado apartments are offered by the night, from {MIN_NIGHT} COP a night. Short stays are tourist rentals: in Colombia they need a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE, which we handle as the property manager (as of November 2026).</p>
      <h2>How to rent one of our El Poblado apartments</h2>
      <ol><li><strong>Pick an apartment</strong> from the list above, or tell us what you need: bedrooms, dates and budget.</li><li><strong>Ask us on WhatsApp or by email.</strong> Write to <a href="mailto:sales@medellinconcierge.net?subject=Furnished%20rental%20inquiry%20%E2%80%93%20El%20Poblado">sales@medellinconcierge.net</a> with your dates, number of guests and budget. We confirm availability and answer your questions about the apartment, the building and the street.</li><li><strong>Agree the stay in writing.</strong> Dates, price, what is included and the house rules.</li><li><strong>Move in.</strong> Our team in El Poblado coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Before you book in El Poblado: a quick checklist</h2>
      <ul><li><strong>Ask where exactly the apartment is.</strong> How steep the walk is, and how far it is from the Metro and from the nightlife streets if you want quiet nights.</li><li><strong>Know the total price.</strong> Ask what it includes (for example utilities, internet and cleaning) and whether anything is charged on top.</li><li><strong>For short stays, check the RNT.</strong> Ask for the listing’s RNT number and look it up on the <a href="https://rnt.confecamaras.co/">public RNT system</a>.</li><li><strong>Get the dates and rules in writing,</strong> including check-in and check-out times and the building’s rules.</li></ul>
      <p>Rules for tourist rentals can change; this reflects how things stand as of November 2026.</p>''',
             faq=[('How much does a furnished apartment in El Poblado cost per month?',
                   'In our listings, as of {AS_OF}, furnished monthly rentals in El Poblado run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the size and the building, plus a one-time cleaning fee. Each apartment on this page shows its current price.'),
                  ('Can I ask about an apartment by email instead of WhatsApp?',
                   'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests and your budget, or use the “Email us about this apartment” button on any listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the total price in writing.'),
                  ('Can I rent an apartment in El Poblado for a few nights?',
                   'Yes. As of {AS_OF}, {N_SHORT} of our El Poblado apartments are offered by the night, from {MIN_NIGHT} COP a night. Short stays are tourist rentals and need an RNT, which we handle for the apartments we manage (as of November 2026).'),
                  ('Is El Poblado a good area to stay in Medellín?',
                   'For many visitors, yes: it has the highest concentration of restaurants, cafés, coworking spaces and malls in the city, and many services in English. The trade-offs are price (guides describe it as the most expensive area), steep streets and weekend noise near the nightlife areas. If you want somewhere quieter, see our rentals in Laureles, Envigado and Sabaneta.'),
                  ('Is El Poblado close to the Metro?',
                   'Metro Line A has two stations at the bottom of the hill, Poblado and Aguacatala. Higher up the hill most people use taxis or ride apps, so ask us how far the apartment you like is from the station.'),
                  ('Do I need a fiador or a deposit?',
                   'Requirements depend on the apartment and the type of stay, so ask us for the exact conditions of the one you like before you book. Our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting without a fiador</a> explains the usual alternatives (general information, not legal advice).'),
                  ('How do I book one of these apartments?',
                   'Tap “Ask about” on the apartment you like, or write to us on WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) or by email (<a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>) with your dates. We confirm availability and agree the details of the stay with you, in English or Spanish.'),
                  ('I own an apartment in El Poblado. Can you rent it out like these?',
                   'Yes. We manage apartments for their owners from 12% of rental income + IVA for stays of 30 nights or more and 17% + IVA for short stays, with no upfront fees. See <a href="../property-management-el-poblado/">property management in El Poblado</a>.')]),
  'es': dict(title='Apartamentos amoblados en arriendo en El Poblado, Medellín',
             desc='Apartamentos amoblados en arriendo en El Poblado, Medellín: {N} por meses o por noches, con precios en vivo. Reserve directo por correo o WhatsApp.',
             h1='Apartamentos amoblados en arriendo en El Poblado',
             crumb='El Poblado',
             lead='<strong>¿Busca un apartamento amoblado en arriendo en El Poblado, Medellín? Al {AS_OF} tenemos {N} apartamentos amoblados disponibles en El Poblado: {N_MONTH} por meses (desde 30 noches), desde {MIN_MONTH} COP al mes, y {N_SHORT} por noches, desde {MIN_NIGHT} COP la noche.</strong> Los administramos nosotros mismos desde nuestra oficina en El Poblado, así que usted reserva directo con el equipo local que los cuida. Pregúntenos por cualquiera por WhatsApp o por correo, en español o en inglés.',
             wa_text='¡Hola! Estoy buscando un apartamento amoblado en El Poblado.',
             mail_subj='Consulta arriendo amoblado – El Poblado',
             lt_h='Arriendo de apartamento amoblado en El Poblado, Medellín, por meses',
             lt_p='{N_MONTH} de los apartamentos de esta lista se arriendan por meses (desde 30 noches), entre {MIN_MONTH} y {MAX_MONTH} COP al mes, directo con el equipo que los administra. Escriba a <a href="{MAIL}">sales@medellinconcierge.net</a> con su fecha de llegada y cuántos meses necesita, y le confirmamos el precio mensual por escrito. Otras zonas: <a href="../arriendos-por-meses-medellin/">arriendos amoblados por meses en Medellín</a>.',
             cta_all='Ver todos los arriendos en Medellín',
             list_h='Apartamentos amoblados en El Poblado disponibles hoy',
             list_intro='Al {AS_OF}: {N} apartamentos amoblados en El Poblado. Precios en pesos colombianos, más una tarifa de aseo única. Toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo y nuestras otras zonas, vea <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.',
             prose='''
      <h2>Cómo es vivir en El Poblado</h2>
      <p>El Poblado es la Comuna 14 de Medellín, una de las 16 comunas de la zona urbana de la ciudad (<a href="https://www.medellin.gov.co/es/conoce-algunos-datos-generales-de-la-ciudad/">Alcaldía de Medellín</a>). Queda en la ladera suroriental y concentra la mayor oferta de hoteles, restaurantes, espacios de coworking y centros comerciales; sectores como el Parque Lleras y Provenza son conocidos por su vida nocturna. Para una primera estadía en Medellín, eso significa tener casi todo cerca y muchos negocios acostumbrados a atender extranjeros.</p>
      <p><strong>Cómo moverse:</strong> la Línea A del Metro tiene las estaciones Poblado y Aguacatala junto al río, en la parte baja de la loma (<a href="https://www.elcolombiano.com/medellin/socavacion-metro-medellin-estaciones-cerradas-AD30117052">El Colombiano</a>). Más arriba, la mayoría se mueve en taxi o en aplicaciones, así que pregúntenos qué tan lejos queda el apartamento de los lugares a los que irá a diario.</p>
      <h2>¿El Poblado es para usted?</h2>
      <ul><li><strong>Le conviene si</strong> quiere ir a pie a cafés, gimnasios y restaurantes, es nuevo en Medellín y quiere servicios en inglés cerca, o le gusta salir de noche.</li><li><strong>Piénselo dos veces si</strong> le molesta el ruido (sobre todo cerca de las calles de rumba los fines de semana), quiere calles planas para caminar o montar en bicicleta (buena parte de El Poblado es empinada) o tiene un presupuesto ajustado: las guías la describen como la zona más cara de la ciudad (<a href="https://www.expatexchange.com/article/5474/Living-in-Colombia-Best-Places-to-Live-in-Medellin,-Colombia">Expat Exchange</a>).</li></ul>
      <p>¿Prefiere algo más tranquilo o más plano? Vea <a href="../arriendos/">nuestros arriendos en Laureles, Envigado y Sabaneta</a>, o compare las zonas en <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado para quedarse un mes</a>.</p>
      <h2>Por meses o por noches: arrendar en El Poblado</h2>
      <p><strong>Por meses (desde 30 noches).</strong> Al {AS_OF}, nuestros {N_MONTH} apartamentos por meses en El Poblado van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según el tamaño y el edificio, más una tarifa de aseo única. Vea todos los apartamentos por meses de la ciudad en nuestra página de <a href="../arriendos-por-meses-medellin/">arriendos por meses en Medellín</a>. Si arrienda por meses, pida un acuerdo claro por escrito; nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica qué revisar.</p>
      <p><strong>Por noches.</strong> Para unas noches o un par de semanas, {N_SHORT} apartamentos en El Poblado se arriendan por noches, desde {MIN_NIGHT} COP la noche. La estancia corta es vivienda turística: en Colombia exige el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia por SIRE, algo que gestionamos nosotros como administradores (a noviembre de 2026).</p>
      <h2>Cómo arrendar uno de nuestros apartamentos en El Poblado</h2>
      <ol><li><strong>Escoja un apartamento</strong> de la lista de arriba, o díganos qué necesita: habitaciones, fechas y presupuesto.</li><li><strong>Pregúntenos por WhatsApp o por correo.</strong> Escriba a <a href="mailto:sales@medellinconcierge.net?subject=Consulta%20arriendo%20amoblado%20%E2%80%93%20El%20Poblado">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son y su presupuesto. Confirmamos la disponibilidad y le resolvemos las dudas sobre el apartamento, el edificio y la cuadra.</li><li><strong>Deje la estadía por escrito.</strong> Fechas, precio, qué incluye y las normas de la casa.</li><li><strong>Instálese.</strong> Nuestro equipo en El Poblado coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Antes de reservar en El Poblado: lista rápida</h2>
      <ul><li><strong>Pregunte dónde queda exactamente.</strong> Qué tan empinado es el camino y qué tan lejos está del Metro y de las calles de rumba, si quiere noches tranquilas.</li><li><strong>Tenga claro el precio total.</strong> Pregunte qué incluye (por ejemplo servicios públicos, internet y aseo) y si se cobra algo aparte.</li><li><strong>Si es por noches, verifique el RNT.</strong> Pida el número de RNT del anuncio y consúltelo en el <a href="https://rnt.confecamaras.co/">sistema público del RNT</a>.</li><li><strong>Deje por escrito fechas y reglas,</strong> incluidos los horarios de llegada y salida y las normas del edificio.</li></ul>
      <p>Las normas de la vivienda turística pueden cambiar; esto refleja cómo están las cosas a noviembre de 2026.</p>''',
             faq=[('¿Cuánto cuesta un apartamento amoblado en El Poblado por mes?',
                   'En nuestras propiedades, al {AS_OF}, los arriendos amoblados por meses en El Poblado van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según el tamaño y el edificio, más una tarifa de aseo única. Cada apartamento de esta página muestra su precio actual.'),
                  ('¿Puedo preguntar por un apartamento por correo en vez de WhatsApp?',
                   'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son y su presupuesto, o use el botón «Escríbanos por este apartamento» de cualquier propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio total.'),
                  ('¿Puedo arrendar un apartamento en El Poblado por unas noches?',
                   'Sí. Al {AS_OF}, {N_SHORT} de nuestros apartamentos en El Poblado se arriendan por noches, desde {MIN_NIGHT} COP la noche. La estancia corta es vivienda turística y exige RNT, que gestionamos para los apartamentos que administramos (a noviembre de 2026).'),
                  ('¿El Poblado es una buena zona para quedarse en Medellín?',
                   'Para muchos visitantes, sí: concentra la mayor oferta de restaurantes, cafés, espacios de coworking y centros comerciales de la ciudad, y muchos servicios en inglés. A cambio, es la zona más cara según las guías, tiene calles empinadas y ruido los fines de semana cerca de la rumba. Si busca algo más tranquilo, vea nuestros arriendos en Laureles, Envigado y Sabaneta.'),
                  ('¿El Poblado queda cerca del Metro?',
                   'La Línea A del Metro tiene dos estaciones en la parte baja de la loma, Poblado y Aguacatala. Más arriba la mayoría se mueve en taxi o en aplicaciones, así que pregúntenos qué tan lejos queda de la estación el apartamento que le guste.'),
                  ('¿Necesito fiador o depósito?',
                   'Los requisitos dependen del apartamento y del tipo de estadía, así que pregúntenos las condiciones exactas del que le guste antes de reservar. Nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo sin fiador</a> explica las alternativas usuales (información general, no asesoría legal).'),
                  ('¿Cómo reservo uno de estos apartamentos?',
                   'Toque «Preguntar por» en el apartamento que le guste, o escríbanos por WhatsApp (<a href="https://wa.me/573042773864">+57 304 277 3864</a>) o por correo (<a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>) con sus fechas. Confirmamos la disponibilidad y acordamos con usted los detalles de la estadía, en español o en inglés.'),
                  ('Tengo un apartamento en El Poblado. ¿Me lo pueden arrendar así?',
                   'Sí. Administramos apartamentos para sus dueños desde el 12% de los ingresos por renta + IVA para estancias de 30 noches o más, y el 17% + IVA para estancias cortas, sin costos iniciales. Vea la <a href="../administracion-de-propiedades-el-poblado/">administración de propiedades en El Poblado</a>.')]),
 },
 'Envigado': {
  'slug': 'envigado',
  'en': dict(title='Furnished Apartments for Rent in Envigado, Medellín',
             desc='Furnished apartments for rent in Envigado, next to Medellín: {N} listed by the month or by the night, with live prices. Book direct by email or WhatsApp.',
             h1='Furnished apartments for rent in Envigado',
             crumb='Envigado',
             lead='<strong>Looking for a furnished apartment for rent in Envigado, just south of Medellín? As of {AS_OF} we have {N} furnished properties in Envigado listed: {N_MONTH} by the month (30 nights or more), from {MIN_MONTH} COP a month, and {N_SHORT} by the night, from {MIN_NIGHT} COP a night.</strong> We manage them ourselves from our office in El Poblado, a short drive away, so you book directly with the local team that looks after them. Ask about any of them by email or on WhatsApp, in English or Spanish.',
             wa_text='Hi! I’m looking for a furnished apartment in Envigado.',
             mail_subj='Furnished rental inquiry – Envigado',
             lt_h='Long-term rentals in Envigado (30+ nights)',
             lt_p='{N_MONTH} of the properties below can be rented long term, by the month (30 nights or more), from {MIN_MONTH} to {MAX_MONTH} COP a month, direct from the team that manages them. Email <a href="{MAIL}">sales@medellinconcierge.net</a> with your move-in date and how many months you need, and we confirm the monthly price in writing. More areas: <a href="../monthly-rentals-medellin/">long-term rentals in Medellín</a>.',
             cta_all='See all rentals in Medellín',
             list_h='Furnished apartments in Envigado available now',
             list_intro='As of {AS_OF}: {N} furnished properties in Envigado. Prices are in Colombian pesos, plus a one-time cleaning fee. Tap “Ask about” and tell us your dates; for live availability and our other areas, see <a href="../rentals/">all our furnished rentals in Medellín</a>.',
             prose='''
      <h2>What Envigado is like to live in</h2>
      <p>Envigado is a separate municipality just south of Medellín and part of the Valle de Aburrá metropolitan area (<a href="https://www.lafm.com.co/colombia/envigado-dijo-si-al-area-metropolitana">La FM</a>); in practice the two cities run into each other. It has its own centre, main park, markets and services, and many parts of it feel like a small town inside the metropolitan area. It is generally less touristic than El Poblado, which is exactly why many people who come to live and work for a while choose it.</p>
      <p><strong>Getting around:</strong> Metro Line A runs south through Ayurá and Envigado stations, so you reach Poblado station in a few stops without changing lines (<a href="https://www.metrodemedellin.gov.co/en/users/integrated-system/line-a">Metro de Medellín, Line A</a>). Parts of Envigado are flat and walkable and others climb the hillside, where most people use taxis or ride apps, so ask us how far an apartment is from the station and from the shops you will use every day.</p>
      <h2>Envigado or El Poblado: which suits your stay?</h2>
      <ul><li><strong>Choose Envigado if you</strong> want quiet nights, room to work from home, local restaurants and markets, and everyday life more than nightlife: remote workers, families and people trying the area before a move.</li><li><strong>Choose El Poblado if you</strong> are new to Medellín, want to walk to cafés, coworking spaces and restaurants, and go out often. See our <a href="../rentals/el-poblado/">furnished apartments for rent in El Poblado</a>.</li></ul>
      <p>Because Envigado lies south of Medellín, the trip to the city’s main sights is longer. Our guide <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado for a month-long stay</a> compares the three areas in detail.</p>
      <h2>Monthly or nightly: renting in Envigado</h2>
      <p><strong>By the month (30 nights or more).</strong> As of {AS_OF}, our {N_MONTH} monthly properties in Envigado run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the size and the type of home, plus a one-time cleaning fee. See every monthly apartment in the city on our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a> page. For a monthly stay, get a clear written agreement; our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains what to check.</p>
      <p><strong>By the night.</strong> For a few nights or a couple of weeks, {N_SHORT} Envigado apartments are offered by the night, from {MIN_NIGHT} COP a night. Short stays are tourist rentals: in Colombia they need a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE, which we handle as the property manager (as of November 2026).</p>
      <h2>How to rent one of our Envigado apartments</h2>
      <ol><li><strong>Pick a property</strong> from the list above, or tell us what you need: bedrooms, dates and budget.</li><li><strong>Email us or ask on WhatsApp.</strong> We confirm availability for your dates and answer your questions about the apartment, the building and the street.</li><li><strong>Agree the stay in writing.</strong> Dates, price, what is included and the house rules.</li><li><strong>Move in.</strong> Our team coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Before you book in Envigado: a quick checklist</h2>
      <ul><li><strong>Ask where exactly the property is.</strong> Whether it is in a flat part or up the hill, and how far it is from the Metro, supermarkets and the main park.</li><li><strong>Know the total price.</strong> Ask what it includes (for example utilities, internet and cleaning) and whether anything is charged on top.</li><li><strong>For short stays, check the RNT.</strong> Ask for the listing’s RNT number and look it up on the <a href="https://rnt.confecamaras.co/">public RNT system</a>.</li><li><strong>Get the dates and rules in writing,</strong> including check-in and check-out times and the building’s rules.</li></ul>
      <p>Rules for tourist rentals can change; this reflects how things stand as of November 2026.</p>''',
             faq=[('How much does a furnished apartment in Envigado cost per month?',
                   'In our listings, as of {AS_OF}, furnished monthly rentals in Envigado run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the size and the type of home, plus a one-time cleaning fee. Each property on this page shows its current price.'),
                  ('Is Envigado part of Medellín?',
                   'No. Envigado is a separate municipality just south of Medellín, part of the Valle de Aburrá metropolitan area, and the two cities run into each other. Metro Line A connects it with El Poblado and the rest of Medellín.'),
                  ('Is Envigado close to the Metro?',
                   'Metro Line A has two stations in Envigado, Ayurá and Envigado, a few stops from Poblado station without changing lines. Parts of Envigado are up the hillside, so ask us how far the apartment you like is from the station.'),
                  ('Can I rent an apartment in Envigado for a few nights?',
                   'Yes. As of {AS_OF}, {N_SHORT} of our Envigado apartments are offered by the night, from {MIN_NIGHT} COP a night. Short stays are tourist rentals and need an RNT, which we handle for the apartments we manage (as of November 2026).'),
                  ('Can I ask about an apartment by email instead of WhatsApp?',
                   'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests and your budget, or use the email button on any listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the price in writing.'),
                  ('Do I need a fiador or a deposit?',
                   'Requirements depend on the apartment and the type of stay, so ask us for the exact conditions of the one you like before you book. Our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting without a fiador</a> explains the usual alternatives (general information, not legal advice).'),
                  ('I own a property in Envigado. Can you rent it out like these?',
                   'Yes. We manage properties for their owners from 12% of rental income + IVA for stays of 30 nights or more and 17% + IVA for short stays, with no upfront fees. See <a href="../property-management-envigado/">property management in Envigado</a>.')]),
  'es': dict(title='Apartamentos amoblados en arriendo en Envigado',
             desc='Apartamentos amoblados en arriendo en Envigado, al lado de Medellín: {N} por meses o por noches, con precios en vivo. Reserve directo por correo o WhatsApp.',
             h1='Apartamentos amoblados en arriendo en Envigado',
             crumb='Envigado',
             lead='<strong>¿Busca un apartamento amoblado en arriendo en Envigado, al sur de Medellín? Al {AS_OF} tenemos {N} propiedades amobladas disponibles en Envigado: {N_MONTH} por meses (desde 30 noches), desde {MIN_MONTH} COP al mes, y {N_SHORT} por noches, desde {MIN_NIGHT} COP la noche.</strong> Las administramos nosotros mismos desde nuestra oficina en El Poblado, a pocos minutos, así que usted reserva directo con el equipo local que las cuida. Pregúntenos por cualquiera por correo o por WhatsApp, en español o en inglés.',
             wa_text='¡Hola! Estoy buscando un apartamento amoblado en Envigado.',
             mail_subj='Consulta arriendo amoblado – Envigado',
             lt_h='Arriendo de apartamento amoblado en Envigado por meses',
             lt_p='{N_MONTH} de las propiedades de esta lista se arriendan por meses (desde 30 noches), entre {MIN_MONTH} y {MAX_MONTH} COP al mes, directo con el equipo que las administra. Escriba a <a href="{MAIL}">sales@medellinconcierge.net</a> con su fecha de llegada y cuántos meses necesita, y le confirmamos el precio mensual por escrito. Otras zonas: <a href="../arriendos-por-meses-medellin/">arriendos amoblados por meses en Medellín</a>.',
             cta_all='Ver todos los arriendos en Medellín',
             list_h='Apartamentos amoblados en Envigado disponibles hoy',
             list_intro='Al {AS_OF}: {N} propiedades amobladas en Envigado. Precios en pesos colombianos, más una tarifa de aseo única. Toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo y nuestras otras zonas, vea <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.',
             prose='''
      <h2>Cómo es vivir en Envigado</h2>
      <p>Envigado es un municipio aparte, pegado a Medellín por el sur, que hace parte del área metropolitana del Valle de Aburrá (<a href="https://www.lafm.com.co/colombia/envigado-dijo-si-al-area-metropolitana">La FM</a>); en el día a día las dos ciudades se confunden. Tiene su propio centro, parque principal, plazas de mercado y servicios, y muchas de sus zonas se sienten como un pueblo dentro del área metropolitana. En general es menos turístico que El Poblado, y justamente por eso lo eligen muchos de quienes vienen a vivir y trabajar una temporada.</p>
      <p><strong>Cómo moverse:</strong> la Línea A del Metro sigue hacia el sur por las estaciones Ayurá y Envigado, así que llega a la estación Poblado en pocas paradas y sin transbordos (<a href="https://www.metrodemedellin.gov.co/en/users/integrated-system/line-a">Metro de Medellín, Línea A</a>). Una parte de Envigado es plana y se camina fácil, y otra sube por la loma, donde la mayoría se mueve en taxi o en aplicaciones; pregúntenos qué tan lejos queda el apartamento de la estación y de los lugares a los que irá a diario.</p>
      <h2>¿Envigado o El Poblado? Cuál le conviene</h2>
      <ul><li><strong>Escoja Envigado si</strong> quiere noches tranquilas, espacio para trabajar desde la casa, restaurantes y mercados de barrio, y vida de todos los días más que rumba: personas que trabajan en remoto, familias y quienes vienen a conocer la zona antes de mudarse.</li><li><strong>Escoja El Poblado si</strong> es nuevo en Medellín, quiere ir a pie a cafés, espacios de coworking y restaurantes, y sale seguido. Vea nuestros <a href="../arriendos/el-poblado/">apartamentos amoblados en arriendo en El Poblado</a>.</li></ul>
      <p>Como Envigado queda al sur de Medellín, el trayecto a los principales sitios turísticos es más largo. Nuestra guía <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado para quedarse un mes</a> compara las tres zonas a fondo.</p>
      <h2>Por meses o por noches: arrendar en Envigado</h2>
      <p><strong>Por meses (desde 30 noches).</strong> Al {AS_OF}, nuestras {N_MONTH} propiedades por meses en Envigado van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según el tamaño y el tipo de vivienda, más una tarifa de aseo única. Vea todos los apartamentos por meses de la ciudad en nuestra página de <a href="../arriendos-por-meses-medellin/">arriendos por meses en Medellín</a>. Si arrienda por meses, pida un acuerdo claro por escrito; nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica qué revisar.</p>
      <p><strong>Por noches.</strong> Para unas noches o un par de semanas, {N_SHORT} apartamentos en Envigado se arriendan por noches, desde {MIN_NIGHT} COP la noche. La estancia corta es vivienda turística: en Colombia exige el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia por SIRE, algo que gestionamos nosotros como administradores (a noviembre de 2026).</p>
      <h2>Cómo arrendar una de nuestras propiedades en Envigado</h2>
      <ol><li><strong>Escoja una propiedad</strong> de la lista de arriba, o díganos qué necesita: habitaciones, fechas y presupuesto.</li><li><strong>Escríbanos por correo o por WhatsApp.</strong> Confirmamos la disponibilidad para sus fechas y le resolvemos las dudas sobre el apartamento, el edificio y la cuadra.</li><li><strong>Deje la estadía por escrito.</strong> Fechas, precio, qué incluye y las normas de la casa.</li><li><strong>Instálese.</strong> Nuestro equipo coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Antes de reservar en Envigado: lista rápida</h2>
      <ul><li><strong>Pregunte dónde queda exactamente.</strong> Si está en la parte plana o loma arriba, y qué tan lejos queda del Metro, del supermercado y del parque principal.</li><li><strong>Tenga claro el precio total.</strong> Pregunte qué incluye (por ejemplo servicios públicos, internet y aseo) y si se cobra algo aparte.</li><li><strong>Si es por noches, verifique el RNT.</strong> Pida el número de RNT del anuncio y consúltelo en el <a href="https://rnt.confecamaras.co/">sistema público del RNT</a>.</li><li><strong>Deje por escrito fechas y reglas,</strong> incluidos los horarios de llegada y salida y las normas del edificio.</li></ul>
      <p>Las normas de la vivienda turística pueden cambiar; esto refleja cómo están las cosas a noviembre de 2026.</p>''',
             faq=[('¿Cuánto cuesta un apartamento amoblado en Envigado por mes?',
                   'En nuestras propiedades, al {AS_OF}, los arriendos amoblados por meses en Envigado van desde {MIN_MONTH} hasta {MAX_MONTH} COP al mes, según el tamaño y el tipo de vivienda, más una tarifa de aseo única. Cada propiedad de esta página muestra su precio actual.'),
                  ('¿Envigado hace parte de Medellín?',
                   'No. Envigado es un municipio aparte, al sur de Medellín, que hace parte del área metropolitana del Valle de Aburrá, y las dos ciudades se confunden. La Línea A del Metro lo conecta con El Poblado y el resto de Medellín.'),
                  ('¿Envigado queda cerca del Metro?',
                   'La Línea A del Metro tiene dos estaciones en Envigado, Ayurá y Envigado, a pocas paradas de la estación Poblado y sin transbordos. Parte de Envigado queda loma arriba, así que pregúntenos qué tan lejos queda de la estación el apartamento que le guste.'),
                  ('¿Puedo arrendar un apartamento en Envigado por unas noches?',
                   'Sí. Al {AS_OF}, {N_SHORT} de nuestros apartamentos en Envigado se arriendan por noches, desde {MIN_NIGHT} COP la noche. La estancia corta es vivienda turística y exige RNT, que gestionamos para los apartamentos que administramos (a noviembre de 2026).'),
                  ('¿Puedo preguntar por un apartamento por correo en vez de WhatsApp?',
                   'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son y su presupuesto, o use el botón de correo de cualquier propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio.'),
                  ('¿Necesito fiador o depósito?',
                   'Los requisitos dependen del apartamento y del tipo de estadía, así que pregúntenos las condiciones exactas del que le guste antes de reservar. Nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo sin fiador</a> explica las alternativas usuales (información general, no asesoría legal).'),
                  ('Tengo una propiedad en Envigado. ¿Me la pueden arrendar así?',
                   'Sí. Administramos propiedades para sus dueños desde el 12% de los ingresos por renta + IVA para estancias de 30 noches o más, y el 17% + IVA para estancias cortas, sin costos iniciales. Vea la <a href="../administracion-de-propiedades-envigado/">administración de propiedades en Envigado</a>.')]),
 },
 'Laureles': {
  'slug': 'laureles',
  'only': 'long_term',   # the copy speaks of monthly stays only; {OTHER_NOTE} and 'no_other' FAQs follow the feed
  'en': dict(title='Furnished Apartments for Rent in Laureles, Medellín',
             desc='Furnished apartments for rent in Laureles, Medellín: {N} listed by the month, with live prices in pesos. Ask by email or WhatsApp and book direct.',
             h1='Furnished apartments for rent in Laureles',
             crumb='Laureles',
             lead='<strong>Looking for a furnished apartment for rent in Laureles, Medellín? As of {AS_OF} we have {N} furnished apartments in Laureles listed by the month (30 nights or more), from {MIN_MONTH} to {MAX_MONTH} COP a month.</strong> We manage them ourselves from our office in El Poblado, so you deal directly with the local team that looks after them. Email us your dates, number of guests and budget, or ask on WhatsApp, in English or Spanish, and we confirm availability and the total price in writing.',
             wa_text='Hi! I’m looking for a furnished apartment in Laureles.',
             mail_subj='Furnished rental inquiry – Laureles',
             lt_h='Long-term rentals in Laureles, Medellín (30+ nights)',
             lt_p='Every apartment below is rented long term, by the month (30 nights or more), direct from the team that manages it. Email <a href="{MAIL}">sales@medellinconcierge.net</a> with your move-in date and how many months you need, and we confirm the monthly price in writing. More areas: <a href="../monthly-rentals-medellin/">long-term rentals in Medellín</a>.',
             cta_all='See all rentals in Medellín',
             list_h='Furnished apartments in Laureles available now',
             list_intro='As of {AS_OF}: {N} furnished apartments in Laureles, by the month. Prices are in Colombian pesos, plus a one-time cleaning fee. Email us or tap “Ask about” and tell us your dates; for live availability and our other areas, see <a href="../rentals/">all our furnished rentals in Medellín</a>.',
             other_none='We have no Laureles apartments by the night at the moment; for a few nights, see <a href="../rentals/">all our furnished apartments for rent in Medellín</a>.',
             other_some='For a few nights, see the Laureles apartments offered by the night on <a href="../rentals/">all our furnished rentals in Medellín</a>.',
             prose='''
      <h2>What Laureles is like to live in</h2>
      <p>Laureles-Estadio lies west of the Medellín River. It is mostly flat, with tree-lined streets, circular avenues and lower buildings than El Poblado, and expat guides often recommend it for its residential, local feel, with plenty of cafés, restaurants and parks (<a href="https://medellinguru.com/guide-to-laureles/">Medellin Guru</a>). Because it is flat, many daily errands can be done on foot.</p>
      <p><strong>Getting around:</strong> Metro Line B serves the area, and Estadio station is close to the Unicentro and Obelisco shopping centres (<a href="https://metrodemedellin.gov.co/en/users/what-to-do-and-where-to-go-in-medellin/commercial-centers">Metro de Medellín</a>). Ask us how far an apartment is from the station and from the supermarket you would use every day.</p>
      <h2>Laureles or El Poblado: which suits your stay?</h2>
      <ul><li><strong>Choose Laureles if you</strong> want a residential neighborhood with a local feel, flat streets to walk and a calm place to work for a month or more: remote workers, slow travellers and people trying the city before a move.</li><li><strong>Choose El Poblado if you</strong> are new to Medellín and want the widest choice of restaurants, coworking spaces and nightlife close by. See our <a href="../rentals/el-poblado/">furnished apartments for rent in El Poblado</a>.</li></ul>
      <p>Our guide <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado for a month-long stay</a> compares the areas in detail, and we also have <a href="../rentals/envigado/">furnished apartments for rent in Envigado</a>.</p>
      <h2>Monthly rentals in Laureles</h2>
      <p>As of {AS_OF}, our {N} furnished apartments in Laureles are offered by the month, from {MIN_MONTH} to {MAX_MONTH} COP a month depending on the size and the building, plus a one-time cleaning fee. Each listing shows its current price. {OTHER_NOTE} For every monthly apartment in the city, see <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a>.</p>
      <p>For a monthly stay, get a clear written agreement; our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting a furnished apartment in Medellín without a fiador</a> explains what to check.</p>
      <h2>How to rent one of our Laureles apartments</h2>
      <ol><li><strong>Pick an apartment</strong> from the list above, or tell us what you need: bedrooms, dates and budget.</li><li><strong>Email us or ask on WhatsApp.</strong> Write to <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, number of guests and budget. We confirm availability and answer your questions about the apartment, the building and the street.</li><li><strong>Agree the stay in writing.</strong> Dates, price, what is included and the house rules.</li><li><strong>Move in.</strong> Our team coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Before you book in Laureles: a quick checklist</h2>
      <ul><li><strong>Ask where exactly the apartment is:</strong> which part of Laureles-Estadio, and how far it is from the Metro and the shops.</li><li><strong>Know the total price.</strong> Ask what it includes (for example utilities, internet and cleaning) and whether anything is charged on top.</li><li><strong>Ask about the workspace and the internet</strong> if you will work from the apartment.</li><li><strong>Get the dates and rules in writing,</strong> including the building’s rules.</li></ul>''',
             faq=[('How much does a furnished apartment in Laureles cost per month?',
                   'In our listings, as of {AS_OF}, furnished monthly rentals in Laureles run from {MIN_MONTH} to {MAX_MONTH} COP a month, depending on the size and the building, plus a one-time cleaning fee. Each apartment on this page shows its current price.'),
                  ('Can I ask about a Laureles apartment by email?',
                   'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests and your budget, or use the email button on a listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the price in writing.'),
                  ('Is Laureles a good area for a stay of a month or more?',
                   'Many longer-stay guests choose it: it is mostly flat and residential, with plenty of cafés, restaurants and parks, and expat guides recommend it for its local feel. It has fewer tourists than El Poblado.'),
                  ('Is Laureles close to the Metro?',
                   'Metro Line B serves the area, and Estadio station is close to the Unicentro and Obelisco shopping centres. Ask us how far the apartment you like is from the station.'),
                  ('Do you have apartments in Laureles by the night?',
                   'Not at the moment: as of {AS_OF} our Laureles apartments are offered by the month (30 nights or more). For a few nights, see <a href="../rentals/">all our furnished rentals in Medellín</a>.', 'no_other'),
                  ('Do I need a fiador or a deposit?',
                   'Requirements depend on the apartment and the type of stay, so ask us for the exact conditions of the one you like before you book. Our guide to <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">renting without a fiador</a> explains the usual alternatives (general information, not legal advice).'),
                  ('I own an apartment in Laureles. Can you rent it out like these?',
                   'Yes. We manage apartments for their owners from 12% of rental income + IVA for stays of 30 nights or more and 17% + IVA for short stays, with no upfront fees. See <a href="../property-management-laureles/">property management in Laureles</a>.')]),
  'es': dict(title='Apartamentos amoblados en arriendo en Laureles',
             desc='Apartamentos amoblados en arriendo en Laureles, Medellín: {N} por meses, con precios en vivo en pesos. Escríbanos por correo o WhatsApp y reserve directo.',
             h1='Apartamentos amoblados en arriendo en Laureles',
             crumb='Laureles',
             lead='<strong>¿Busca un apartamento amoblado en arriendo en Laureles, Medellín? Al {AS_OF} tenemos {N} apartamentos amoblados en Laureles por meses (desde 30 noches), entre {MIN_MONTH} y {MAX_MONTH} COP al mes.</strong> Los administramos nosotros mismos desde nuestra oficina en El Poblado, así que usted trata directo con el equipo local que los cuida. Escríbanos por correo con sus fechas, cuántas personas son y su presupuesto, o pregúntenos por WhatsApp, en español o en inglés, y le confirmamos por escrito la disponibilidad y el precio total.',
             wa_text='¡Hola! Estoy buscando un apartamento amoblado en Laureles.',
             mail_subj='Consulta arriendo amoblado – Laureles',
             lt_h='Arriendo de apartamento amoblado en Laureles, Medellín, por meses',
             lt_p='Todos los apartamentos de esta lista se arriendan por meses (desde 30 noches), directo con el equipo que los administra. Escriba a <a href="{MAIL}">sales@medellinconcierge.net</a> con su fecha de llegada y cuántos meses necesita, y le confirmamos el precio mensual por escrito. Otras zonas: <a href="../arriendos-por-meses-medellin/">arriendos amoblados por meses en Medellín</a>.',
             cta_all='Ver todos los arriendos en Medellín',
             list_h='Apartamentos amoblados en Laureles disponibles hoy',
             list_intro='Al {AS_OF}: {N} apartamentos amoblados en Laureles, por meses. Precios en pesos colombianos, más una tarifa de aseo única. Escríbanos o toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo y nuestras otras zonas, vea <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.',
             other_none='Por ahora no tenemos apartamentos en Laureles por noches; para pocas noches, vea <a href="../arriendos/">todos nuestros apartamentos amoblados en arriendo en Medellín</a>.',
             other_some='Para pocas noches, vea los apartamentos en Laureles por noches en <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.',
             prose='''
      <h2>Cómo es vivir en Laureles</h2>
      <p>Laureles-Estadio queda al occidente del río Medellín. Es mayormente plano, con calles arborizadas, circulares y edificios más bajos que en El Poblado, y las guías para extranjeros lo recomiendan por su ambiente residencial y de barrio, con muchos cafés, restaurantes y parques (<a href="https://medellinguru.com/guide-to-laureles/">Medellin Guru</a>). Como es plano, muchas vueltas del día a día se hacen a pie.</p>
      <p><strong>Cómo moverse:</strong> la Línea B del Metro pasa por la zona y la estación Estadio queda cerca de los centros comerciales Unicentro y Obelisco (<a href="https://metrodemedellin.gov.co/en/users/what-to-do-and-where-to-go-in-medellin/commercial-centers">Metro de Medellín</a>). Pregúntenos qué tan lejos queda el apartamento de la estación y del supermercado que usaría a diario.</p>
      <h2>¿Laureles o El Poblado? Cuál le conviene</h2>
      <ul><li><strong>Escoja Laureles si</strong> quiere un barrio residencial con ambiente local, calles planas para caminar y un lugar tranquilo para trabajar durante un mes o más: personas que trabajan en remoto, que viajan sin afán o que vienen a probar la ciudad antes de mudarse.</li><li><strong>Escoja El Poblado si</strong> es su primera vez en Medellín y quiere tener cerca la mayor oferta de restaurantes, coworkings y vida nocturna. Vea nuestros <a href="../arriendos/el-poblado/">apartamentos amoblados en arriendo en El Poblado</a>.</li></ul>
      <p>Nuestra guía <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado para quedarse un mes</a> compara las zonas a fondo, y también tenemos <a href="../arriendos/envigado/">apartamentos amoblados en arriendo en Envigado</a>.</p>
      <h2>Apartamentos amoblados por meses en Laureles</h2>
      <p>Al {AS_OF}, nuestros {N} apartamentos amoblados en Laureles se arriendan por meses, entre {MIN_MONTH} y {MAX_MONTH} COP al mes según el tamaño y el edificio, más una tarifa de aseo única. Cada propiedad muestra su precio actual. {OTHER_NOTE} Para ver todos los que se arriendan por meses en la ciudad, vea <a href="../arriendos-por-meses-medellin/">apartamentos amoblados por meses en Medellín</a>.</p>
      <p>Si arrienda por meses, pida un acuerdo claro por escrito; nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo amoblado en Medellín sin fiador</a> explica qué revisar.</p>
      <h2>Cómo arrendar uno de nuestros apartamentos en Laureles</h2>
      <ol><li><strong>Escoja un apartamento</strong> de la lista de arriba, o díganos qué necesita: habitaciones, fechas y presupuesto.</li><li><strong>Escríbanos por correo o por WhatsApp.</strong> Envíe sus fechas, cuántas personas son y su presupuesto a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>. Confirmamos la disponibilidad y le resolvemos las dudas sobre el apartamento, el edificio y la cuadra.</li><li><strong>Deje la estadía por escrito.</strong> Fechas, precio, qué incluye y las normas de la casa.</li><li><strong>Instálese.</strong> Nuestro equipo coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Antes de reservar en Laureles: lista rápida</h2>
      <ul><li><strong>Pregunte dónde queda exactamente:</strong> en qué parte de Laureles-Estadio y qué tan lejos del Metro y del comercio.</li><li><strong>Tenga claro el precio total.</strong> Pregunte qué incluye (por ejemplo servicios públicos, internet y aseo) y si se cobra algo aparte.</li><li><strong>Si va a trabajar desde el apartamento,</strong> pregunte por el espacio de trabajo y el internet.</li><li><strong>Deje por escrito fechas y reglas,</strong> incluido el reglamento del edificio.</li></ul>''',
             faq=[('¿Cuánto cuesta un apartamento amoblado en Laureles al mes?',
                   'En nuestras propiedades, al {AS_OF}, los arriendos amoblados por meses en Laureles van de {MIN_MONTH} a {MAX_MONTH} COP al mes, según el tamaño y el edificio, más una tarifa de aseo única. Cada apartamento de esta página muestra su precio actual.'),
                  ('¿Puedo preguntar por un apartamento en Laureles por correo?',
                   'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son y su presupuesto, o use el botón de correo de la propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio.'),
                  ('¿Laureles es buen sector para quedarse un mes o más?',
                   'Muchos huéspedes de estadías largas lo escogen: es mayormente plano y residencial, con muchos cafés, restaurantes y parques, y las guías para extranjeros lo recomiendan por su ambiente de barrio. Tiene menos turistas que El Poblado.'),
                  ('¿Laureles queda cerca del Metro?',
                   'La Línea B del Metro pasa por la zona y la estación Estadio queda cerca de los centros comerciales Unicentro y Obelisco. Pregúntenos qué tan lejos queda de la estación el apartamento que le guste.'),
                  ('¿Tienen apartamentos amoblados en Laureles por días?',
                   'Por ahora no: al {AS_OF} nuestros apartamentos en Laureles se arriendan por meses (desde 30 noches). Para pocas noches, vea <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.', 'no_other'),
                  ('¿Necesito fiador o depósito?',
                   'Los requisitos dependen del apartamento y del tipo de estadía, así que pregúntenos las condiciones exactas del que le guste antes de reservar. Nuestra guía de <a href="../blog/rent-furnished-apartment-medellin-without-fiador.html">arriendo sin fiador</a> explica las alternativas usuales (información general, no asesoría legal).'),
                  ('Tengo un apartamento en Laureles. ¿Me lo pueden arrendar así?',
                   'Sí. Administramos apartamentos para sus dueños desde el 12% de los ingresos por renta + IVA para estancias de 30 noches o más, y el 17% + IVA para estancias cortas, sin costos iniciales. Vea la <a href="../administracion-de-propiedades-laureles/">administración de propiedades en Laureles</a>.')]),
 },
 'Sabaneta': {
  'slug': 'sabaneta',
  'only': 'short_term',
  'en': dict(title='Furnished Apartments for Rent in Sabaneta, Colombia',
             desc='Furnished apartments for rent in Sabaneta, just south of Medellín: {N} listed by the night, with live prices. Ask by email or WhatsApp and book direct.',
             h1='Furnished apartments for rent in Sabaneta',
             crumb='Sabaneta',
             lead='<strong>Looking for a furnished apartment for rent in Sabaneta, just south of Medellín? As of {AS_OF} we have {N} furnished apartments in Sabaneta listed by the night, from {MIN_NIGHT} COP a night.</strong> We manage them ourselves, so you book directly with the local team that looks after them. Email us your dates and number of guests, or ask on WhatsApp, in English or Spanish, and we confirm availability and the total price in writing.',
             wa_text='Hi! I’m looking for a furnished apartment in Sabaneta.',
             mail_subj='Furnished rental inquiry – Sabaneta',
             cta_all='See all rentals in Medellín',
             list_h='Furnished apartments in Sabaneta available now',
             list_intro='As of {AS_OF}: {N} furnished apartments in Sabaneta, by the night. Prices are in Colombian pesos, plus a one-time cleaning fee. Email us or tap “Ask about” and tell us your dates; for live availability and our other areas, see <a href="../rentals/">all our furnished rentals in Medellín</a>.',
             other_none='We have no Sabaneta apartment listed by the month at the moment. If you need 30 nights or more, email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates and we tell you what is available, or see our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a>.',
             other_some='For 30 nights or more, see the Sabaneta apartments offered by the month on our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a> page.',
             prose='''
      <h2>What Sabaneta is like to stay in</h2>
      <p>Sabaneta is a separate municipality in the south of the Valle de Aburrá, next to Envigado, and is often described as the smallest municipality in Colombia by area (<a href="https://www.bluradio.com/turismo/el-municipio-mas-pequeno-de-colombia-esta-en-antioquia-y-tiene-planes-imperdibles-so35">Blu Radio</a>). It is compact and residential, with its own main park and local life, and quieter than El Poblado.</p>
      <p><strong>Getting around:</strong> Sabaneta station on Metro Line A sits between Itagüí and La Estrella, so you ride north to Poblado station and the rest of Medellín without changing lines (<a href="https://en.wikipedia.org/wiki/Sabaneta_station">Sabaneta station</a>; <a href="https://www.metrodemedellin.gov.co/en/users/integrated-system/line-a">Metro de Medellín, Line A</a>). Ask us how far an apartment is from the station and from the main park.</p>
      <h2>Sabaneta, Envigado or El Poblado: which suits your stay?</h2>
      <ul><li><strong>Choose Sabaneta if you</strong> want a calm, residential base with a direct Metro ride into Medellín: families, remote workers and people visiting relatives or getting to know the south of the valley. Because it lies south of Envigado, the trip to El Poblado and the city centre is longer.</li><li><strong>Prefer to be closer in?</strong> See our <a href="../rentals/envigado/">furnished apartments for rent in Envigado</a> or <a href="../rentals/el-poblado/">in El Poblado</a>.</li></ul>
      <h2>Renting in Sabaneta by the night or by the month</h2>
      <p><strong>By the night.</strong> As of {AS_OF}, our {N} Sabaneta apartments are offered by the night, from {MIN_NIGHT} COP a night, plus a one-time cleaning fee. Short stays are tourist rentals: in Colombia they need a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE, which we handle as the property manager (as of November 2026).</p>
      <p><strong>By the month.</strong> {OTHER_NOTE}</p>
      <h2>How to rent one of our Sabaneta apartments</h2>
      <ol><li><strong>Pick an apartment</strong> from the list above, or tell us your dates and how many guests.</li><li><strong>Email us or ask on WhatsApp.</strong> Write to <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates and number of guests. We confirm availability and answer your questions about the apartment, the building and the street.</li><li><strong>Agree the stay in writing.</strong> Dates, price, what is included and the house rules.</li><li><strong>Move in.</strong> Our team coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Before you book in Sabaneta: a quick checklist</h2>
      <ul><li><strong>Ask where exactly the apartment is</strong> and how far it is from Sabaneta station and the main park.</li><li><strong>Know the total price for your dates,</strong> including the cleaning fee.</li><li><strong>Check the RNT.</strong> Ask for the listing’s RNT number and look it up on the <a href="https://rnt.confecamaras.co/">public RNT system</a>.</li><li><strong>Get the dates and the building’s rules in writing,</strong> including check-in and check-out times.</li></ul>
      <p>Rules for tourist rentals can change; this reflects how things stand as of November 2026.</p>''',
             faq=[('How much does a furnished apartment in Sabaneta cost per night?',
                   'In our listings, as of {AS_OF}, furnished apartments in Sabaneta start from {MIN_NIGHT} COP a night, plus a one-time cleaning fee. Each apartment on this page shows its current price.'),
                  ('Can I ask about a Sabaneta apartment by email?',
                   'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates and the number of guests, or use the email button on a listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the price in writing.'),
                  ('Is Sabaneta part of Medellín?',
                   'No. Sabaneta is a separate municipality in the south of the Valle de Aburrá, next to Envigado. Metro Line A connects it with El Poblado and the rest of Medellín.'),
                  ('Is Sabaneta on the Metro?',
                   'Yes. Sabaneta station is on Metro Line A, between Itagüí and La Estrella, with a direct ride north to Poblado station.'),
                  ('Can I rent a furnished apartment in Sabaneta by the month?',
                   'As of {AS_OF} our Sabaneta apartments are listed by the night. Email us your dates for a stay of 30 nights or more and we tell you what is available, or see our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a>.', 'no_other'),
                  ('I own an apartment in Sabaneta. Can you rent it out like these?',
                   'Yes. We manage apartments for their owners from 17% of rental income + IVA for short stays and 12% + IVA for stays of 30 nights or more, with no upfront fees. See <a href="../property-management-sabaneta/">property management in Sabaneta</a>.')]),
  'es': dict(title='Apartamentos amoblados en arriendo en Sabaneta',
             desc='Apartamentos amoblados en Sabaneta, Antioquia: {N} en arriendo por días, con precios en vivo. Escríbanos por correo o WhatsApp y reserve directo.',
             h1='Apartamentos amoblados en arriendo en Sabaneta',
             crumb='Sabaneta',
             lead='<strong>¿Busca un apartamento amoblado en arriendo en Sabaneta, Antioquia? Al {AS_OF} tenemos {N} apartamentos amoblados en Sabaneta por días, desde {MIN_NIGHT} COP la noche.</strong> Los administramos nosotros mismos, así que usted reserva directo con el equipo local que los cuida. Escríbanos por correo con sus fechas y cuántas personas son, o pregúntenos por WhatsApp, y le confirmamos por escrito la disponibilidad y el precio total.',
             wa_text='¡Hola! Estoy buscando un apartamento amoblado en Sabaneta.',
             mail_subj='Consulta arriendo amoblado – Sabaneta',
             cta_all='Ver todos los arriendos en Medellín',
             list_h='Apartamentos amoblados en Sabaneta disponibles hoy',
             list_intro='Al {AS_OF}: {N} apartamentos amoblados en Sabaneta, por días. Precios en pesos colombianos, más una tarifa de aseo única. Escríbanos o toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo y nuestras otras zonas, vea <a href="../arriendos/">todos nuestros arriendos amoblados en Medellín</a>.',
             other_none='Por ahora no tenemos un apartamento en Sabaneta publicado por meses. Si necesita 30 noches o más, escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas y le decimos qué hay disponible, o vea nuestros <a href="../arriendos-por-meses-medellin/">apartamentos amoblados por meses en Medellín</a>.',
             other_some='Para 30 noches o más, vea los apartamentos en Sabaneta por meses en nuestra página de <a href="../arriendos-por-meses-medellin/">apartamentos amoblados por meses en Medellín</a>.',
             prose='''
      <h2>Cómo es quedarse en Sabaneta</h2>
      <p>Sabaneta es un municipio aparte, en el sur del Valle de Aburrá y vecino de Envigado, y se le conoce como el municipio más pequeño de Colombia por extensión (<a href="https://www.bluradio.com/turismo/el-municipio-mas-pequeno-de-colombia-esta-en-antioquia-y-tiene-planes-imperdibles-so35">Blu Radio</a>). Es compacto y residencial, con su parque principal y vida de barrio, y más tranquilo que El Poblado.</p>
      <p><strong>Cómo moverse:</strong> la estación Sabaneta de la Línea A del Metro queda entre Itagüí y La Estrella, así que usted sube hasta la estación Poblado y el resto de Medellín sin hacer transbordos (<a href="https://en.wikipedia.org/wiki/Sabaneta_station">estación Sabaneta</a>; <a href="https://www.metrodemedellin.gov.co/en/users/integrated-system/line-a">Metro de Medellín, Línea A</a>). Pregúntenos qué tan lejos queda el apartamento de la estación y del parque principal.</p>
      <h2>¿Sabaneta, Envigado o El Poblado? Cuál le conviene</h2>
      <ul><li><strong>Escoja Sabaneta si</strong> quiere una base tranquila y residencial con Metro directo a Medellín: familias, personas que trabajan en remoto y quienes visitan parientes o vienen a conocer el sur del valle. Como queda al sur de Envigado, el trayecto a El Poblado y al centro es más largo.</li><li><strong>¿Prefiere quedar más cerca?</strong> Vea nuestros <a href="../arriendos/envigado/">apartamentos amoblados en arriendo en Envigado</a> o <a href="../arriendos/el-poblado/">en El Poblado</a>.</li></ul>
      <h2>Apartamentos amoblados en Sabaneta por días o por meses</h2>
      <p><strong>Por días.</strong> Al {AS_OF}, nuestros {N} apartamentos en Sabaneta se arriendan por noches, desde {MIN_NIGHT} COP la noche, más una tarifa de aseo única. La renta corta es vivienda turística: en Colombia exige el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia por SIRE, algo que gestionamos nosotros como administradores (a noviembre de 2026).</p>
      <p><strong>Por meses.</strong> {OTHER_NOTE}</p>
      <h2>Cómo arrendar uno de nuestros apartamentos en Sabaneta</h2>
      <ol><li><strong>Escoja un apartamento</strong> de la lista de arriba, o díganos sus fechas y cuántas personas son.</li><li><strong>Escríbanos por correo o por WhatsApp.</strong> Envíe sus fechas y cuántas personas son a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a>. Confirmamos la disponibilidad y le resolvemos las dudas sobre el apartamento, el edificio y la cuadra.</li><li><strong>Deje la estadía por escrito.</strong> Fechas, precio, qué incluye y las normas de la casa.</li><li><strong>Instálese.</strong> Nuestro equipo coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Antes de reservar en Sabaneta: lista rápida</h2>
      <ul><li><strong>Pregunte dónde queda exactamente</strong> y qué tan lejos está de la estación Sabaneta y del parque principal.</li><li><strong>Tenga claro el precio total para sus fechas,</strong> con la tarifa de aseo.</li><li><strong>Verifique el RNT.</strong> Pida el número de RNT del anuncio y consúltelo en el <a href="https://rnt.confecamaras.co/">sistema público del RNT</a>.</li><li><strong>Deje por escrito fechas y reglas,</strong> incluidos los horarios de llegada y salida y el reglamento del edificio.</li></ul>
      <p>Las normas de la vivienda turística pueden cambiar; esto refleja cómo están las cosas a noviembre de 2026.</p>''',
             faq=[('¿Cuánto cuesta un apartamento amoblado en Sabaneta por noche?',
                   'En nuestras propiedades, al {AS_OF}, los apartamentos amoblados en Sabaneta van desde {MIN_NIGHT} COP la noche, más una tarifa de aseo única. Cada apartamento de esta página muestra su precio actual.'),
                  ('¿Puedo preguntar por un apartamento en Sabaneta por correo?',
                   'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas y cuántas personas son, o use el botón de correo de la propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio.'),
                  ('¿Sabaneta hace parte de Medellín?',
                   'No. Sabaneta es un municipio aparte, en el sur del Valle de Aburrá y vecino de Envigado. La Línea A del Metro lo conecta con El Poblado y el resto de Medellín.'),
                  ('¿Sabaneta tiene Metro?',
                   'Sí. La estación Sabaneta está en la Línea A, entre Itagüí y La Estrella, con viaje directo hacia el norte hasta la estación Poblado.'),
                  ('¿Arriendan apartamentos amoblados en Sabaneta por meses?',
                   'Al {AS_OF} nuestros apartamentos en Sabaneta están publicados por noches. Escríbanos con sus fechas para una estadía de 30 noches o más y le decimos qué hay disponible, o vea nuestros <a href="../arriendos-por-meses-medellin/">apartamentos amoblados por meses en Medellín</a>.', 'no_other'),
                  ('Tengo un apartamento en Sabaneta. ¿Me lo pueden arrendar así?',
                   'Sí. Administramos apartamentos para sus dueños desde el 17% de los ingresos por renta + IVA para estancias cortas y el 12% + IVA para estancias de 30 noches o más, sin costos iniciales. Vea la <a href="../administracion-de-propiedades-sabaneta/">administración de propiedades en Sabaneta</a>.')]),
 },
}

def area_stats(lang, area, only=None):
    P = [p for p in LISTINGS['properties'] if rl_area(p) == area and (not only or p['stay_type'] == only)]
    month = [rl_price(p) for p in P if p['stay_type'] == 'long_term' and rl_price(p)]
    night = [rl_price(p) for p in P if p['stay_type'] == 'short_term' and rl_price(p)]
    return {'{AS_OF}': human_date(LISTINGS['as_of'] or TODAY, lang), '{N}': str(len(P)),
            '{N_MONTH}': str(sum(p['stay_type'] == 'long_term' for p in P)), '{N_SHORT}': str(sum(p['stay_type'] == 'short_term' for p in P)),
            '{MIN_MONTH}': cop(min(month)) if month else '—', '{MAX_MONTH}': cop(max(month)) if month else '—',
            '{MIN_NIGHT}': cop(min(night)) if night else '—'}, P, month, night

def deeper(h):   # page() output assumes one folder below /rentals/-level; these pages sit one more folder down
    return re.sub(r'(src|href)="\.\./', r'\1="../../', h)

RA_MUNICIPALITIES = {'Envigado', 'Sabaneta'}   # separate municipalities, not neighborhoods of Medellín
RA_LIVE = []   # (area, slug) of area rental pages built this run, for links from /rentals/
for area, cfg in RA.items():
    only = cfg.get('only')   # single-stay-type areas: copy speaks of that type; page lists only that type
    st0, P, month, night = area_stats('en', area, only)
    if len(P) < 2 or (not only and (not month or not night)) or (only == 'long_term' and not month) or (only == 'short_term' and not night):
        print(f'  note: rentals/{cfg["slug"]}/ skipped ({len(P)} listings in {area}; needs 2+ with the prices its copy quotes)')
        continue
    has_other = bool(only) and any(rl_area(p) == area and p['stay_type'] != only for p in LISTINGS['properties'])
    RA_LIVE.append((area, cfg['slug']))
    en_url, es_url = SITE + f'rentals/{cfg["slug"]}/', SITE + f'es/arriendos/{cfg["slug"]}/'
    for lang in LANGS:
        ui = cfg[lang]; st = area_stats(lang, area, only)[0]
        if only: st['{OTHER_NOTE}'] = fill(ui['other_some' if has_other else 'other_none'], st)
        url = es_url if lang == 'es' else en_url
        home_url = SITE + ('es/' if lang == 'es' else '')
        rentals_rel, rentals_url = (('../rentals/', SITE + 'rentals/') if lang == 'en' else ('../arriendos/', SITE + 'es/arriendos/'))
        rentals_name = R[lang]['crumb']
        faq = [(fill(f[0], st), fill(f[1], st)) for f in ui['faq'] if not (len(f) > 2 and f[2] == 'no_other' and has_other)]
        faq_html = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in faq)
        wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(ui['wa_text'])
        body_txt = MAIL[lang]['body'].replace('El Poblado, Laureles, Envigado, other', area).replace('El Poblado, Laureles, Envigado, otra', area)
        mhref = mailto(ui['mail_subj'], body_txt)
        # R13 (Nov 25 2026, office reports mc-2026-11-23/25): long-term H2 above the listings, only when the feed has monthly listings here
        lt_html = (f'<div class="prose"><h2>{ui["lt_h"]}</h2><p>{fill(ui["lt_p"], st).replace("{MAIL}", mhref)}</p></div>'
                   if ui.get('lt_h') and st['{N_MONTH}'] != '0' and only in (None, 'long_term') else '')
        desc = fill(ui['desc'], st)
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{R[lang]["home"]}</a> / <a href="{rentals_rel}">{rentals_name}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{fill(ui["lead"], st)}</div>
    <div class="ref-ctas"><a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">WhatsApp</a><a class="btn btn-ghost" href="{mhref}">{MAIL[lang]["btn"]}</a><a class="btn btn-ghost" href="{rentals_rel}">{ui["cta_all"]}</a></div>
    {mail_note(lang, MAIL[lang]["short"] + " ")}
  </div>
</section>
<section class="rentals">
  <div class="wrap">
    {lt_html}
    {rl_section(lang, st, only=only, h=ui['list_h'], intro=ui['list_intro'], area=area)}
    {mail_block(lang, 'rentals', href=mhref, wa_text=ui['wa_text'])}
    <div class="prose">{fill(ui["prose"], st)}
      <h2>{L[lang]["faq_h"]}</h2>
      <div class="faq">
{faq_html}      </div>
    </div>
    <aside class="article-cta">
      <h2>{R[lang]["owners_h"]}</h2>
      <p>{R[lang]["owners_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{R[lang]["owners_cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>'''
        schema = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'CollectionPage', 'name': ui['h1'], 'description': desc, 'url': url, 'inLanguage': lang,
             'about': {'@type': 'Place', 'name': f'{area}, Medellín' if area not in RA_MUNICIPALITIES else f'{area}, Antioquia', 'address': {'@type': 'PostalAddress', 'addressLocality': area if area in RA_MUNICIPALITIES else 'Medellín', 'addressRegion': 'Antioquia', 'addressCountry': 'CO'}},
             'publisher': mail_publisher()},
            {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
                {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in faq]},
            breadcrumbs([(R[lang]['home'], home_url), (rentals_name, rentals_url), (ui['crumb'], url)]),
            rl_schema(lang, url, only=only, name=ui['list_h'], area=area)]}
        en_href, es_href = ((f'./', f'../es/arriendos/{cfg["slug"]}/') if lang == 'en' else (f'../../rentals/{cfg["slug"]}/', './'))
        folder = f'rentals/{cfg["slug"]}' if lang == 'en' else f'es/arriendos/{cfg["slug"]}'
        write(f'{folder}/index.html', deeper(page(lang, title=ui['title'], desc=desc, en_url=en_url, es_url=es_url,
              en_href=en_href, es_href=es_href, body=body, schema=schema)))
    SITEMAP.append((en_url, es_url, TODAY))


# ======================= 4c4. Short-term rentals (/short-term-rentals-medellin/, /es/apartamentos-por-dias-medellin/) =======================
# Backlog R6 (James, Nov 22 2026: "more ways to show up for renters"). Every listing offered by the night in the HostFlow
# feed, grouped by area, with an answer-first summary from the feed's own numbers, email + WhatsApp CTAs and FAQ.
# Targets "short term rentals medellin", "vacation rentals medellin" / "apartamentos por días medellín". No minimum
# nights, check-in times or payment methods are stated here: they are not confirmed (ask us).
# R12 (Nov 25 2026, office report mc-2026-11-23/25): 'vacation rentals' / 'alquiler vacacional' in title, meta, H2 and FAQ.
S = {
 'en': dict(slug='short-term-rentals-medellin', home='Home', rentals='Rentals', rentals_url='rentals/', crumb='Short-term rentals',
            title='Short-Term & Vacation Rentals in Medellín | Book Direct',
            desc='Short-term and vacation rentals in Medellín: {N_SHORT} furnished apartments by the night, from {MIN_NIGHT} COP. Email us your dates and book direct.',
            h1='Short-term rentals in Medellín: furnished apartments by the night',
            lead='<strong>Looking for a short-term rental in Medellín for a few nights or a couple of weeks? We rent furnished apartments by the night, and you book directly with the local team that manages them.</strong> As of {AS_OF}, {N_SHORT} short-term rentals are listed with a price, from {MIN_NIGHT} COP a night plus a one-time cleaning fee, in {SHORT_AREAS}. Email us your dates or ask on WhatsApp, in English or Spanish, and we confirm availability and the total price in writing.',
            cta_wa='Ask about a short stay', wa_text='Hi! I’m looking for a furnished apartment in Medellín for a short stay.', cta_all='See all rentals with live availability',
            list_h='Short-term rentals available now',
            list_intro='As of {AS_OF}, “from” prices in Colombian pesos per night, plus a one-time cleaning fee. Tap “Ask about” and tell us your dates; for live availability, see <a href="../rentals/">all our furnished rentals</a>. Jump to: {JUMP}',
            area_h='Short-term rentals in {A}', area_p='{n} apartments by the night, from {min} COP a night.', area_one='1 apartment by the night, from {min} COP a night.',
            area_more='More in {A}: <a href="../rentals/{slug}/">furnished apartments for rent in {A}</a>, by the night and by the month.',
            other_h='More short-term rentals in and around Medellín', other_p='Also by the night: {LIST}.',
            label={'Medellín': 'Medellín (other neighborhoods)'},
            prose="""
      <h2>Vacation rentals in Medellín, booked direct</h2>
      <p><strong>Every short-term rental on this page is also a vacation rental: a furnished apartment our own team manages, rented by the night, in {SHORT_AREAS}.</strong> You book directly with us, not through a platform, and you get one written quote with the total price for your dates, including the cleaning fee. Prices on this page come from our booking system and are dated {AS_OF}. <a href="{MAIL_VAC}">Email us your dates and number of guests</a> and we reply with the apartments that are free, in English or Spanish.</p>
      <p>A vacation rental suits a holiday, a family visit or a group trip, when you want a kitchen, a living room and more space than a hotel room. For stays of 30 nights or more, our <a href="../monthly-rentals-medellin/">monthly rentals</a> are priced by the month.</p>
      <h2>What is a short-term rental in Medellín?</h2>
      <p>A short-term rental is a furnished apartment you rent by the night, ready to live in from the day you arrive: a kitchen, your own space and a local team a message away. It suits a holiday, a business trip, a family visit, or a first week in the city while you look for a <a href="../monthly-rentals-medellin/">monthly rental</a>. Each listing on this page shows a “from” price per night and a one-time cleaning fee; as of {AS_OF}, cleaning fees on our short-term rentals run from {MIN_CLEAN_S} to {MAX_CLEAN_S} COP. The price for your exact dates comes in our written quote.</p>
      <h2>How to book a short-term rental with us</h2>
      <ol><li><strong>Choose an apartment</strong> from the list above, or tell us what you need: area, bedrooms, number of guests and dates.</li><li><strong>Email us or ask on WhatsApp.</strong> Write to <a href="mailto:sales@medellinconcierge.net?subject=Furnished%20rental%20inquiry%20%E2%80%93%20short%20stay">sales@medellinconcierge.net</a> or tap “Ask about” on a listing. We answer in English or Spanish.</li><li><strong>Get your quote in writing.</strong> We confirm availability, the total price for your dates including the cleaning fee, and the house rules.</li><li><strong>Arrive.</strong> Our local team, based in El Poblado, coordinates your check-in, and guests can reach us 24/7 during the stay.</li></ol>
      <h2>Short stays in Colombia: RNT and SIRE</h2>
      <p>Renting an apartment by the night is a tourist rental. In Colombia it needs a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE; as the property manager, we handle both for the apartments we manage (as of November 2026). Before you book any short-term rental in Medellín, ask for the listing’s RNT number and look it up on the <a href="https://rnt.confecamaras.co/">public RNT system</a>. Rules for tourist rentals can change; this reflects how things stand as of November 2026.</p>
      <h2>Short stay or monthly rental?</h2>
      <p>If you are staying 30 nights or more, our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a> are priced by the month instead of by the night. Not sure where to stay? El Poblado has the most restaurants, cafés and nightlife; Envigado and Sabaneta, just south of Medellín, are quieter and good for everyday life. Read <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado vs Laureles vs Envigado</a> to compare.</p>
      <h2>Before you book: a short-stay checklist</h2>
      <ul><li><strong>Check the RNT</strong> on the public RNT system.</li><li><strong>Know the total price,</strong> including the cleaning fee and anything charged on top.</li><li><strong>Get the dates and rules in writing,</strong> including check-in and check-out times and the building’s rules.</li><li><strong>Know who to call.</strong> Make sure someone answers 24/7 if something goes wrong during your stay.</li></ul>""",
            faq=[('How much does a short-term rental in Medellín cost?',
                  'In our listings, as of {AS_OF}, furnished apartments by the night run from {MIN_NIGHT} to {MAX_NIGHT} COP a night, depending on the area, the size and the building, plus a one-time cleaning fee. Each listing on this page shows its current “from” price; we confirm the total for your dates in writing.'),
                 ('Are these vacation rentals?',
                  'Yes. In Colombia, renting a furnished apartment by the night to tourists is a tourist rental (vivienda turística), the same thing many sites call a vacation rental. Every apartment on this page is one we manage, rented by the night from {MIN_NIGHT} COP as of {AS_OF}, and booked directly with our team by email or WhatsApp.'),
                 ('Is there a cleaning fee for short stays?',
                  'Yes. Each listing shows a one-time cleaning fee, charged once per stay; as of {AS_OF}, cleaning fees on our short-term rentals run from {MIN_CLEAN_S} to {MAX_CLEAN_S} COP.'),
                 ('Can I ask about an apartment by email instead of WhatsApp?',
                  'Yes. Email <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> with your dates, the number of guests, your budget and the area you prefer, or use the “Email us about this apartment” button on any listing so the apartment is named for you. We answer in English or Spanish and confirm availability and the total price in writing.'),
                 ('What is the minimum stay?',
                  'It depends on the apartment and your dates, so ask us: send your dates by email or WhatsApp and we tell you what is available. For 30 nights or more, see our <a href="../monthly-rentals-medellin/">monthly rentals in Medellín</a>.'),
                 ('How does check-in work?',
                  'Our local team, based in El Poblado, coordinates your check-in and confirms the check-in and check-out times of your apartment in writing before you arrive. During the stay you can reach us 24/7.'),
                 ('How do I pay for a short-term rental?',
                  'When we confirm your dates, we send you the total price, including the cleaning fee, and how to pay, in writing. Ask us any question about payment before you book.'),
                 ('Do your short-term rentals have an RNT?',
                  'Short stays in Colombia need a Registro Nacional de Turismo (RNT), and as the property manager we handle RNT, SIRE and TRA for the properties we manage (as of November 2026). Ask us for the RNT number of the apartment you like and check it on the public RNT system.'),
                 ('Which areas are your short-term rentals in?',
                  'As of {AS_OF}: {SHORT_AREA_COUNTS}. The list on this page shows the current ones.')]),
 'es': dict(slug='es/apartamentos-por-dias-medellin', home='Inicio', rentals='Arriendos', rentals_url='es/arriendos/', crumb='Apartamentos por días',
            title='Apartamentos por días y alquiler vacacional en Medellín',
            desc='Apartamentos por días y alquiler vacacional en Medellín: {N_SHORT} amoblados por noches, desde {MIN_NIGHT} COP. Escríbanos sus fechas y reserve directo.',
            h1='Apartamentos por días en Medellín: amoblados, por noches',
            lead='<strong>¿Busca un apartamento por días en Medellín para unas noches o un par de semanas? Arrendamos apartamentos amoblados por noches, y usted reserva directo con el equipo local que los administra.</strong> Al {AS_OF} hay {N_SHORT} apartamentos por días con precio, desde {MIN_NIGHT} COP la noche más una tarifa de aseo única, en {SHORT_AREAS}. Escríbanos sus fechas por correo o por WhatsApp, en español o en inglés, y le confirmamos por escrito la disponibilidad y el precio total.',
            cta_wa='Preguntar por una estadía corta', wa_text='¡Hola! Busco un apartamento amoblado en Medellín por días.', cta_all='Ver todos los arriendos con disponibilidad en vivo',
            list_h='Apartamentos por días disponibles hoy',
            list_intro='Al {AS_OF}, precios «desde» en pesos colombianos por noche, más una tarifa de aseo única. Toque «Preguntar por» y díganos sus fechas; para la disponibilidad en vivo, vea <a href="../arriendos/">todos nuestros arriendos amoblados</a>. Ir a: {JUMP}',
            area_h='Apartamentos por días en {A}', area_p='{n} apartamentos por noches, desde {min} COP la noche.', area_one='1 apartamento por noches, desde {min} COP la noche.',
            area_more='Más en {A}: <a href="../arriendos/{slug}/">apartamentos amoblados en arriendo en {A}</a>, por noches y por meses.',
            other_h='Más apartamentos por días en Medellín y sus alrededores', other_p='También por noches: {LIST}.',
            label={'Medellín': 'Medellín (otros barrios)'},
            prose="""
      <h2>Alquiler vacacional en Medellín, con reserva directa</h2>
      <p><strong>Todos los apartamentos por días de esta página son también apartamentos vacacionales: amoblados, administrados por nuestro propio equipo y arrendados por noches en {SHORT_AREAS}.</strong> Usted reserva directo con nosotros, sin plataforma de por medio, y recibe una sola cotización por escrito con el precio total de sus fechas, aseo incluido. Los precios de esta página salen de nuestro sistema de reservas y están fechados al {AS_OF}. <a href="{MAIL_VAC}">Escríbanos sus fechas y cuántas personas son</a> y le respondemos con los apartamentos libres, en español o en inglés.</p>
      <p>Un apartamento vacacional sirve para unas vacaciones, la visita de la familia o un viaje en grupo, cuando quiere cocina, sala y más espacio que una habitación de hotel. Para 30 noches o más, nuestros <a href="../arriendos-por-meses-medellin/">arriendos por meses</a> tienen precio mensual.</p>
      <h2>¿Qué es un apartamento por días en Medellín?</h2>
      <p>Un apartamento por días es un apartamento amoblado que se arrienda por noches, listo para vivir desde el día en que llega: cocina, su propio espacio y un equipo local a un mensaje de distancia. Sirve para unas vacaciones, un viaje de trabajo, una visita familiar o la primera semana en la ciudad mientras busca un <a href="../arriendos-por-meses-medellin/">arriendo por meses</a>. Cada propiedad de esta página muestra un precio «desde» por noche y una tarifa de aseo única; al {AS_OF}, el aseo en nuestros apartamentos por días va desde {MIN_CLEAN_S} hasta {MAX_CLEAN_S} COP. El precio para sus fechas exactas se lo enviamos por escrito.</p>
      <h2>Cómo reservar un apartamento por días con nosotros</h2>
      <ol><li><strong>Escoja un apartamento</strong> de la lista de arriba, o díganos qué necesita: zona, habitaciones, cuántas personas son y las fechas.</li><li><strong>Escríbanos por correo o por WhatsApp.</strong> Escriba a <a href="mailto:sales@medellinconcierge.net?subject=Consulta%20arriendo%20amoblado%20%E2%80%93%20por%20d%C3%ADas">sales@medellinconcierge.net</a> o toque «Preguntar por» en una propiedad. Respondemos en español o en inglés.</li><li><strong>Reciba la cotización por escrito.</strong> Le confirmamos la disponibilidad, el precio total de sus fechas con el aseo incluido y las normas de la casa.</li><li><strong>Llegue.</strong> Nuestro equipo local, con oficina en El Poblado, coordina su llegada, y durante la estadía nos encuentra 24/7.</li></ol>
      <h2>Estancias cortas en Colombia: RNT y SIRE</h2>
      <p>Arrendar un apartamento por noches es vivienda turística. En Colombia exige el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia por SIRE; como administradores, gestionamos ambos en los apartamentos que administramos (a noviembre de 2026). Antes de reservar cualquier apartamento por días en Medellín, pida el número de RNT del anuncio y consúltelo en el <a href="https://rnt.confecamaras.co/">sistema público del RNT</a>. Las normas de la vivienda turística pueden cambiar; esto refleja cómo están las cosas a noviembre de 2026.</p>
      <h2>¿Por días o por meses?</h2>
      <p>Si se queda 30 noches o más, nuestros <a href="../arriendos-por-meses-medellin/">arriendos por meses en Medellín</a> tienen precio mensual en vez de por noche. ¿No sabe dónde quedarse? El Poblado tiene la mayor oferta de restaurantes, cafés y vida nocturna; Envigado y Sabaneta, al sur de Medellín, son más tranquilos y buenos para la vida diaria. Lea <a href="../blog/where-to-stay-in-medellin-for-a-month.html">El Poblado, Laureles o Envigado</a> para compararlos.</p>
      <h2>Antes de reservar: lista para una estadía corta</h2>
      <ul><li><strong>Verifique el RNT</strong> en el sistema público del RNT.</li><li><strong>Tenga claro el precio total,</strong> con el aseo y cualquier cobro adicional.</li><li><strong>Deje por escrito fechas y reglas,</strong> incluidos los horarios de llegada y salida y las normas del edificio.</li><li><strong>Sepa a quién llamar.</strong> Asegúrese de que alguien responda 24/7 si algo pasa durante su estadía.</li></ul>""",
            faq=[('¿Cuánto cuesta un apartamento por días en Medellín?',
                  'En nuestras propiedades, al {AS_OF}, los apartamentos amoblados por noches van desde {MIN_NIGHT} hasta {MAX_NIGHT} COP la noche, según la zona, el tamaño y el edificio, más una tarifa de aseo única. Cada propiedad de esta página muestra su precio «desde» actual; el total de sus fechas se lo confirmamos por escrito.'),
                 ('¿Son apartamentos de alquiler vacacional?',
                  'Sí. En Colombia, arrendar un apartamento amoblado por noches a turistas es vivienda turística, lo que muchas páginas llaman alquiler vacacional. Todos los apartamentos de esta página los administramos nosotros, se arriendan por noches desde {MIN_NIGHT} COP al {AS_OF} y se reservan directo con nuestro equipo por correo o por WhatsApp.'),
                 ('¿Se cobra aseo en las estadías cortas?',
                  'Sí. Cada propiedad muestra una tarifa de aseo única, que se cobra una vez por estadía; al {AS_OF}, el aseo en nuestros apartamentos por días va desde {MIN_CLEAN_S} hasta {MAX_CLEAN_S} COP.'),
                 ('¿Puedo preguntar por un apartamento por correo en vez de WhatsApp?',
                  'Sí. Escriba a <a href="mailto:sales@medellinconcierge.net">sales@medellinconcierge.net</a> con sus fechas, cuántas personas son, su presupuesto y la zona que prefiere, o use el botón «Escríbanos por este apartamento» de cualquier propiedad para que el apartamento quede indicado. Respondemos en español o en inglés y le confirmamos por escrito la disponibilidad y el precio total.'),
                 ('¿Cuál es la estadía mínima?',
                  'Depende del apartamento y de sus fechas, así que pregúntenos: envíenos sus fechas por correo o por WhatsApp y le decimos qué hay disponible. Para 30 noches o más, vea nuestros <a href="../arriendos-por-meses-medellin/">arriendos por meses en Medellín</a>.'),
                 ('¿Cómo es la llegada (check-in)?',
                  'Nuestro equipo local, con oficina en El Poblado, coordina su llegada y le confirma por escrito, antes de que llegue, los horarios de entrada y salida de su apartamento. Durante la estadía nos encuentra 24/7.'),
                 ('¿Cómo pago un apartamento por días?',
                  'Cuando confirmamos sus fechas, le enviamos por escrito el precio total, con el aseo incluido, y cómo pagar. Pregúntenos cualquier duda sobre el pago antes de reservar.'),
                 ('¿Sus apartamentos por días tienen RNT?',
                  'La renta corta en Colombia exige el Registro Nacional de Turismo (RNT), y como administradores gestionamos el RNT, el SIRE y la TRA de las propiedades que administramos (a noviembre de 2026). Pídanos el número de RNT del apartamento que le guste y consúltelo en el sistema público del RNT.'),
                 ('¿En qué zonas están sus apartamentos por días?',
                  'Al {AS_OF}: {SHORT_AREA_COUNTS}. La lista de esta página muestra los actuales.')]),
}

def short_stats(lang):
    ui = S[lang]; P = [p for p in LISTINGS['properties'] if p['stay_type'] == 'short_term']
    night = [rl_price(p) for p in P if rl_price(p)]
    clean = [p['cleaning_fee'] for p in P if p.get('cleaning_fee')]
    n = {}
    for p in P: n[rl_area(p)] = n.get(rl_area(p), 0) + 1
    areas = sorted(n, key=lambda a: (-n[a], a))
    lab = lambda a: ui['label'].get(a, a)
    st = rl_stats(lang)
    st.update({'{MIN_NIGHT}': cop(min(night)) if night else '—', '{MAX_NIGHT}': cop(max(night)) if night else '—',
               '{MIN_CLEAN_S}': cop(min(clean)) if clean else '—', '{MAX_CLEAN_S}': cop(max(clean)) if clean else '—',
               '{SHORT_AREAS}': rl_join([lab(a) for a in areas], lang), '{TOP_AREAS}': ', '.join(areas[:3]),
               '{SHORT_AREA_COUNTS}': rl_join([f'{a} ({n[a]})' for a in areas], lang),
               '{MAIL_VAC}': mail_href(lang, 'vacation')})
    return st, P, n, areas

def short_list(lang, st, P, n, areas):
    """Nightly listings grouped by area: an H2 per area with 2+ listings, the rest under one closing H2."""
    ui = S[lang]; lab = lambda a: ui['label'].get(a, a)
    big = [a for a in areas if n[a] >= 2]; small = [a for a in areas if n[a] < 2]
    aid = lambda a: 'area-' + re.sub(r'[^a-z]+', '-', unicodedata.normalize('NFKD', a).encode('ascii', 'ignore').decode().lower()).strip('-')
    jump = ' · '.join([f'<a href="#{aid(a)}">{a}</a>' for a in big] + ([f'<a href="#area-more">{ui["other_h"]}</a>'] if small else []))
    out = f'<section class="rl" aria-labelledby="rl-h"><h2 id="rl-h">{ui["list_h"]}</h2><p class="rl-intro">{fill(ui["list_intro"], st).replace("{JUMP}", jump)}</p>'
    slugs = dict(RA_LIVE)
    for a in big:
        grp = sorted((p for p in P if rl_area(p) == a), key=rl_sort)
        mn = min(rl_price(p) for p in grp if rl_price(p))
        out += (f'<h2 id="{aid(a)}">{ui["area_h"].format(A=a)}</h2><p class="rl-intro">{ui["area_p"].format(n=len(grp), min=cop(mn))}'
                + (' ' + ui['area_more'].format(A=a, slug=slugs[a]) if a in slugs else '') + '</p>'
                + '<ul class="rl-list">' + ''.join(rl_item(p, lang) for p in grp) + '</ul>')
    if small:
        grp = sorted((p for p in P if rl_area(p) in small), key=rl_sort)
        out += (f'<h2 id="area-more">{ui["other_h"]}</h2><p class="rl-intro">{ui["other_p"].replace("{LIST}", rl_join([f"{a} ({n[a]})" for a in small], lang))}</p>'
                + '<ul class="rl-list">' + ''.join(rl_item(p, lang) for p in grp) + '</ul>')
    return out + '</section>'

if sum(p['stay_type'] == 'short_term' and bool(rl_price(p)) for p in LISTINGS['properties']) >= 2:
    for lang in LANGS:
        ui = S[lang]; st, P, n, areas = short_stats(lang)
        en_url, es_url = SITE + S['en']['slug'] + '/', SITE + S['es']['slug'] + '/'
        url = es_url if lang == 'es' else en_url
        home_url = SITE + ('es/' if lang == 'es' else '')
        pre = '../' if lang == 'en' else '../../'
        faq = [(fill(q, st), fill(a, st)) for q, a in ui['faq']]
        faq_html = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in faq)
        wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(ui['wa_text'])
        desc = fill(ui['desc'], st)
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / <a href="{pre}{ui["rentals_url"]}">{ui["rentals"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{fill(ui["lead"], st)}</div>
    <div class="ref-ctas"><a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">{ui["cta_wa"]}</a><a class="btn btn-ghost" href="{mail_href(lang, 'short')}">{MAIL[lang]["btn"]}</a><a class="btn btn-ghost" href="{pre}{ui["rentals_url"]}">{ui["cta_all"]}</a></div>
    {mail_note(lang, MAIL[lang]["short"] + " ")}
  </div>
</section>
<section class="rentals">
  <div class="wrap">
    {short_list(lang, st, P, n, areas)}
    {mail_block(lang, 'short', wa_text=ui['wa_text'])}
    <div class="prose">{fill(ui["prose"], st)}
      <h2>{L[lang]["faq_h"]}</h2>
      <div class="faq">
{faq_html}      </div>
    </div>
    <aside class="article-cta">
      <h2>{R[lang]["owners_h"]}</h2>
      <p>{R[lang]["owners_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{R[lang]["owners_cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>'''
        schema = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'CollectionPage', 'name': ui['h1'], 'description': desc, 'url': url, 'inLanguage': lang,
             'publisher': mail_publisher()},
            {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
                {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in faq]},
            breadcrumbs([(ui['home'], home_url), (ui['rentals'], SITE + ui['rentals_url']), (ui['crumb'], url)]),
            rl_schema(lang, url, only='short_term', name=ui['list_h'])]}
        en_href, es_href = (('./', '../es/apartamentos-por-dias-medellin/') if lang == 'en' else ('../../short-term-rentals-medellin/', './'))
        write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=desc, en_url=en_url, es_url=es_url,
              en_href=en_href, es_href=es_href, body=body, schema=schema))
    SITEMAP.append((SITE + 'short-term-rentals-medellin/', SITE + 'es/apartamentos-por-dias-medellin/', TODAY))
else:
    print('  note: short-term-rentals-medellin/ skipped (fewer than 2 priced nightly listings in the feed)')


# ======================= 4c5. Renter blog posts: "Furnished rentals by area" row (backlog R11) =======================
RENTER_ROW = {
 'en': dict(h='Furnished rentals by area', label='Furnished rentals by area',
            p='Every apartment on these pages is one we manage, listed with its current price. Email us your dates and we answer with what is available.',
            all=('rentals/', 'All furnished apartments for rent in Medellín'),
            month=('monthly-rentals-medellin/', 'Monthly rentals in Medellín (30+ nights)'),
            short=('short-term-rentals-medellin/', 'Short-term rentals in Medellín, by the night'),
            area='rentals/{slug}/', area_t='Furnished apartments for rent in {area}'),
 'es': dict(h='Arriendos amoblados por zona', label='Arriendos amoblados por zona',
            p='Todos los apartamentos de estas páginas los administramos nosotros y aparecen con su precio actual. Escríbanos sus fechas y le respondemos con lo que está disponible.',
            all=('arriendos/', 'Todos los apartamentos amoblados en arriendo en Medellín'),
            month=('arriendos-por-meses-medellin/', 'Arriendos amoblados por meses en Medellín (30+ noches)'),
            short=('apartamentos-por-dias-medellin/', 'Apartamentos por días en Medellín'),
            area='arriendos/{slug}/', area_t='Apartamentos amoblados en arriendo en {area}'),
}
_built = {u for u, _, _ in SITEMAP}
for path, post_html, lang in RENTER_POST_WRITES:
    c = RENTER_ROW[lang]
    links = [c['all'], c['month']]
    if SITE + 'short-term-rentals-medellin/' in _built: links.append(c['short'])
    links += [(c['area'].format(slug=slug), c['area_t'].format(area=area)) for area, slug in RA_LIVE]
    links = [(h, t) for h, t in links if os.path.exists(os.path.join(ROOT, ('' if lang == 'en' else 'es/') + h, 'index.html'))]
    row = (f'<nav class="more-posts" aria-label="{c["label"]}">\n      <h2>{c["h"]}</h2>\n      <p>{c["p"]}</p>\n'
           + '\n'.join(f'      <a href="../{h}">{t}</a>' for h, t in links) + '\n    </nav>')
    write(path, post_html.replace(RENTER_ROW_MARK, row))


# ======================= 4d. Meet the team (/team/, /es/equipo/) =======================
# People and roles are in team.py; photos (on white, 4:5) in assets/team/, made by team_photos.py.
T = {
 'en': dict(slug='team', home='Home', crumb='Team',
            title='Meet the Team | Medellín Concierge',
            desc='Meet the Medellín Concierge team: the managers who look after your property, your guests and your monthly statements in Medellín, Colombia.',
            h1='Meet the team',
            lead='The people who manage your property, look after your guests and keep your accounts in order in Medellín. Together we run <a href="../">property management in Medellín</a>, from <a href="../airbnb-management-medellin/">Airbnb management</a> to <a href="../long-term-property-management-medellin/">long-term rentals</a>.',
            cta_h='Talk to our team', cta_p='Get a free consultation, an income estimate and a management proposal.'),
 'es': dict(slug='es/equipo', home='Inicio', crumb='Equipo',
            title='Nuestro equipo | Medellín Concierge',
            desc='Conozca al equipo de Medellín Concierge: quienes cuidan su propiedad, atienden a sus huéspedes y preparan sus estados mensuales en Medellín.',
            h1='Conozca a nuestro equipo',
            lead='Las personas que administran su propiedad, atienden a sus huéspedes y llevan sus cuentas en orden en Medellín. Juntos hacemos la <a href="../">administración de propiedades en Medellín</a>, desde la <a href="../administracion-de-airbnb-medellin/">administración de Airbnb</a> hasta las <a href="../administracion-de-rentas-largas-medellin/">rentas largas</a>.',
            cta_h='Hable con nuestro equipo', cta_p='Solicite una consulta gratuita, una estimación de ingresos y una propuesta de administración.'),
}

def initials(name):
    return ''.join(w[0] for w in name.split()[:2]).upper()

for lang in LANGS:
    ui = T[lang]
    en_url, es_url = SITE + T['en']['slug'] + '/', SITE + T['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    prefix = '../' if lang == 'en' else '../../'
    cards_html = ''
    for m in TEAM:
        has_photo = os.path.exists(os.path.join(ROOT, 'assets', 'team', m['photo'] + '.webp'))
        photo = (f'<img src="{prefix}assets/team/{m["photo"]}.webp" alt="{html.escape(m["name"])}" width="640" height="800" loading="lazy" decoding="async">'
                 if has_photo else f'<span class="initials" aria-hidden="true">{initials(m["name"])}</span>')
        bio = f'\n          <p class="member-bio">{html.escape(m["bio"][lang])}</p>' if m.get('bio') else ''
        cards_html += (f'      <article class="member">\n        <div class="member-photo">{photo}</div>\n'
                       f'        <div class="member-text">\n          <h2>{html.escape(m["name"])}</h2>\n'
                       f'          <p class="member-role">{html.escape(m["role"][lang])}</p>{bio}\n        </div>\n      </article>\n')
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="team">
  <div class="wrap">
    <div class="team-grid">
{cards_html}    </div>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#contact">{L[lang]["cta_1"]}</a><a class="btn btn-outline" href="https://wa.me/573042773864">WhatsApp</a></div>
    </aside>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'AboutPage', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'about': {'@id': business_id()},
         'mainEntity': [{'@type': 'Person', 'name': m['name'], 'jobTitle': m['role'][lang],
                         **({'description': m['bio'][lang]} if m.get('bio') else {}),
                         'worksFor': {'@id': business_id()},
                         **({'image': SITE + 'assets/team/' + m['photo'] + '.webp'}
                            if os.path.exists(os.path.join(ROOT, 'assets', 'team', m['photo'] + '.webp')) else {})} for m in TEAM]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/equipo/') if lang == 'en' else ('../../team/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'team/', SITE + 'es/equipo/', TODAY))


# ======================= 4f. FAQ (/faq/, /es/preguntas-frecuentes/) =======================
# Questions and answers live in faq.py (brochure FAQs + the former home-page FAQ). FAQPage structured data here.
F = {
 'en': dict(slug='faq', home='Home', crumb='FAQ', title='Property Management FAQ | Medellín Concierge',
            desc='Answers to owners’ questions about our Airbnb and long-term property management in Medellín: services, fees, payouts, guests, cleaning and RNT.',
            h1='Frequently asked questions', lead='Straight answers about how we manage your property in Medellín. For the full picture, see <a href="../">property management in Medellín</a>, <a href="../airbnb-management-medellin/">Airbnb management</a>, <a href="../long-term-property-management-medellin/">long-term rentals</a> and <a href="../property-management-fees-medellin/">our fees</a>.',
            cta_h='Still have a question?', cta_p='Write to us or book a free consultation. We reply in English or Spanish.'),
 'es': dict(slug='es/preguntas-frecuentes', home='Inicio', crumb='Preguntas frecuentes',
            title='Administración de propiedades: preguntas frecuentes',
            desc='Respuestas a las preguntas de los propietarios sobre nuestra administración de Airbnb y rentas largas en Medellín: servicios, tarifas, pagos y RNT.',
            h1='Preguntas frecuentes', lead='Respuestas claras sobre cómo administramos su propiedad en Medellín. Para ver el panorama completo, consulte <a href="../">administración de propiedades en Medellín</a>, <a href="../administracion-de-airbnb-medellin/">administración de Airbnb</a>, <a href="../administracion-de-rentas-largas-medellin/">rentas largas</a> y <a href="../tarifas-administracion-de-propiedades-medellin/">nuestras tarifas</a>.',
            cta_h='¿Tiene otra pregunta?', cta_p='Escríbanos o solicite una consulta gratuita. Respondemos en español o en inglés.'),
}
for lang in LANGS:
    ui = F[lang]
    en_url, es_url = SITE + F['en']['slug'] + '/', SITE + F['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    qa = [(item[lang][0], item[lang][1].replace('{home}', '../')) for item in FAQ]
    items = ''.join(f'      <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in qa)
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="faq-page">
  <div class="wrap">
    <div class="faq">
{items}    </div>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#contact">{L[lang]["cta_1"]}</a><a class="btn btn-outline" href="https://wa.me/573042773864">WhatsApp</a></div>
    </aside>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in qa]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/preguntas-frecuentes/') if lang == 'en' else ('../../faq/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'faq/', SITE + 'es/preguntas-frecuentes/', TODAY))


# ======================= 4h. Fees (/property-management-fees-medellin/, /es/tarifas-administracion-de-propiedades-medellin/) =======================
# Answer-first fees page for "how much does property management cost in Medellín". Copy lives in fees.py.
for lang in LANGS:
    ui = FEES[lang]
    en_url, es_url = SITE + FEES['en']['slug'] + '/', SITE + 'es/' + FEES['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    secs = ''.join(f'\n      <h2>{h}</h2>\n      {b}' for h, b in ui['sections'])
    items = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in ui['faq'])
    more = ''.join(f'<a href="{h}">{t}</a>' for h, t in ui['more'])
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{ui["lead"]}</div>
    {rating_line(lang)}
  </div>
</section>
<article class="article landing">
  <div class="wrap">
    <div class="prose">{secs}
      <h2>{ui["faq_h"]}</h2>
      <div class="faq">
{items}      </div>
    </div>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#contact">{L[lang]["cta_1"]}</a><a class="btn btn-outline" href="https://wa.me/573042773864">WhatsApp</a></div>
    </aside>
    <nav class="more-posts" aria-label="{ui["more_h"]}">
      <h2>{ui["more_h"]}</h2>
      {more}
    </nav>
  </div>
</article>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', 'name': ui['h1'], 'url': url, 'inLanguage': lang, 'description': ui['desc'],
         'about': {'@id': business_id()}},
        {'@type': 'Service', 'name': ui['h1'], 'serviceType': L[lang]['service'], 'url': url, 'inLanguage': lang,
         'provider': provider_ref(), 'areaServed': {'@type': 'Place', 'name': 'Medellín'}},
        {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in ui['faq']]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    if lang == 'en':
        en_href, es_href = './', f'../es/{FEES["es"]["slug"]}/'
    else:
        en_href, es_href = f'../../{FEES["en"]["slug"]}/', './'
    folder = FEES['en']['slug'] if lang == 'en' else 'es/' + FEES['es']['slug']
    write(f'{folder}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + FEES['en']['slug'] + '/', SITE + 'es/' + FEES['es']['slug'] + '/', TODAY))


# ======================= 4i. Revenue calculator (/airbnb-revenue-calculator/, /es/calculadora-ingresos-airbnb-medellin/) =======================
# The old Wix URL as a real page: the home page's calculator widget (section + inline script, copied from the built
# home pages so they never drift apart) wrapped in answer-first copy from calculator.py.
_js = en[en.index('  // Revenue calculator (illustrative)'):]
_js = _js[:_js.index('\n  suggestRate(); calc();\n') + len('\n  suggestRate(); calc();')]   # the initial call, not the one inside the click handler
for lang in LANGS:
    ui = CALC[lang]
    home_html = es if lang == 'es' else en
    widget = home_html[home_html.index('<section id="calculator" class="dark">'):]
    widget = widget[:widget.index('</section>') + len('</section>')]
    widget = re.sub(r'\s*reveal(?=")', '', widget).replace('href="#contact"', 'href="../#contact"')
    widget = re.sub(r'<p class="lead">.*?</p>\n?', '', widget, count=1, flags=re.S)
    en_url, es_url = SITE + CALC['en']['slug'] + '/', SITE + 'es/' + CALC['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    secs = ''.join(f'\n      <h2>{h}</h2>\n      {b}' for h, b in ui['sections'])
    items = ''.join(f'        <details><summary>{html.escape(q, quote=False)}{PLUS}</summary><p>{a}</p></details>\n' for q, a in ui['faq'])
    more = ''.join(f'<a href="{h}">{t}</a>' for h, t in ui['more'])
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <div class="lead">{ui["lead"]}</div>
    {rating_line(lang)}
  </div>
</section>
{widget}
<article class="article landing">
  <div class="wrap">
    <div class="prose">
      {ui["after_calc"]}{secs}
      <h2>{ui["faq_h"]}</h2>
      <div class="faq">
{items}      </div>
    </div>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#contact">{L[lang]["cta_1"]}</a><a class="btn btn-outline" href="https://wa.me/573042773864">WhatsApp</a></div>
    </aside>
    <nav class="more-posts" aria-label="{ui["more_h"]}">
      <h2>{ui["more_h"]}</h2>
      {more}
    </nav>
  </div>
</article>
<script>
{_js}
</script>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', 'name': ui['h1'], 'url': url, 'inLanguage': lang, 'description': ui['desc'],
         'about': {'@id': business_id()}},
        {'@type': 'WebApplication', 'name': ui['h1'], 'url': url, 'inLanguage': lang, 'description': ui['desc'],
         'applicationCategory': 'FinanceApplication', 'operatingSystem': 'Any', 'isAccessibleForFree': True,
         'provider': provider_ref()},
        {'@type': 'FAQPage', 'url': url, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in ui['faq']]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    if lang == 'en':
        en_href, es_href = './', f'../es/{CALC["es"]["slug"]}/'
    else:
        en_href, es_href = f'../../{CALC["en"]["slug"]}/', './'
    folder = CALC['en']['slug'] if lang == 'en' else 'es/' + CALC['es']['slug']
    write(f'{folder}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + CALC['en']['slug'] + '/', SITE + 'es/' + CALC['es']['slug'] + '/', TODAY))


# ======================= 4g. Tours (/tours/, /es/tours/) =======================
# Viator partner widget (tours and activities). Viator renders it in its own iframe, so its cards and
# buttons follow the settings in the Viator partner dashboard; everything around it uses our branding.
VIATOR = ('<div data-vi-partner-id="U00208834" data-vi-widget-ref="W-5fd2b915-458a-4723-9670-97c7a88fdf7b"></div>\n'
          '      <script async src="https://www.viator.com/orion/partner/widget.js"></script>')
TOURS = {
 'en': dict(slug='tours', home='Home', crumb='Tours', title='Tours in Medellín | Medellín Concierge',
            desc='Tours and day trips in and around Medellín: Guatapé, Comuna 13, coffee farms and more, booked online through our partner Viator.',
            h1='Tours in Medellín', lead='Day trips and experiences in and around Medellín, booked online through our partner Viator.',
            note='Tours are run by independent local operators and booked and paid on Viator. Medellín Concierge may earn a commission on bookings.',
            cta_h='Own a property in Medellín?', cta_p='We manage homes for their owners, from listing to monthly GAAP statements.',
            cta='See our management plans'),
 'es': dict(slug='es/tours', home='Inicio', crumb='Tours', title='Tours en Medellín | Medellín Concierge',
            desc='Tours y paseos de un día en Medellín y alrededores: Guatapé, Comuna 13, fincas cafeteras y más, reservados en línea con nuestro aliado Viator.',
            h1='Tours en Medellín', lead='Paseos de un día y experiencias en Medellín y sus alrededores, reservados en línea con nuestro aliado Viator.',
            note='Los tours los operan empresas locales independientes y se reservan y pagan en Viator. Medellín Concierge puede recibir una comisión por las reservas.',
            cta_h='¿Tiene una propiedad en Medellín?', cta_p='Administramos propiedades para sus dueños, desde la publicación hasta los estados financieros mensuales bajo GAAP.',
            cta='Ver nuestros planes de administración'),
}
for lang in LANGS:
    ui = TOURS[lang]
    en_url, es_url = SITE + 'tours/', SITE + 'es/tours/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="tours">
  <div class="wrap">
    <div class="tours-embed">
      {VIATOR}
    </div>
    <p class="tours-note">{ui["note"]}</p>
    <aside class="article-cta">
      <h2>{ui["cta_h"]}</h2>
      <p>{ui["cta_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{ui["cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'publisher': {'@id': business_id()}},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/tours/') if lang == 'en' else ('../../tours/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'tours/', SITE + 'es/tours/', TODAY))


# ======================= 4h. Commercial management (/commercial/, /es/comercial/) =======================
# Hotels, full buildings and community hospitality operations. Same Hostflow lead form as the home page.
LEAD_FORM = 'https://hostflow.in/lead?t=49d-bifpnoxA37UexXu3HOgg&amp;lang='
COMMERCIAL_ICONS = [
    '<path d="M3 20V8m0 6h18v6M3 14h18M7 11.5a1.5 1.5 0 1 0 0-.01M11 11h7a3 3 0 0 1 3 3"/>',                       # bed
    '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2M11 21v-3h2v3"/>',  # building
    '<circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 5M18 20a6 6 0 0 0-3-5.2"/>',     # people
]
COMMERCIAL = {
 'en': dict(slug='commercial', home='Home', crumb='Commercial',
            title='Hotel & Building Management in Medellín | Medellín Concierge',
            desc='Commercial hospitality management in Medellín: we run hotels and full buildings for their owners, from distribution and pricing to guests and monthly reports.',
            h1='Commercial hospitality management',
            lead='Hotels, full buildings and community hospitality operations in Medellín, run for their owners by the same team and systems that manage our apartments.',
            who_h='Who we work with',
            who=[('Hotels and boutique hotels', 'Independent hotels that want stronger online distribution, smarter pricing and dependable guest service, without giving up their own identity.'),
                 ('Full buildings', 'Aparthotels and buildings of furnished units run as one operation: every unit priced, cleaned, maintained and reported together.'),
                 ('Community hospitality', 'Coliving, residential communities and buildings that mix short and long stays, where guests and residents share the same spaces.')],
            run_h='What we run for you',
            run_lead='One operator for the whole property, with one point of contact for owners and investors.',
            run=['Distribution on Airbnb, Booking.com, Expedia and VRBO, with synced calendars and dynamic pricing',
                 '24/7 guest support: reservations, check-ins and guest communication',
                 'Housekeeping and maintenance, coordinated and supervised',
                 'Common areas, house rules and resident relations in shared buildings',
                 'RNT, SIRE and TRA registrations and reporting',
                 'Owner portal with monthly GAAP financial statements'],
            how_h='How we take over an operation',
            how=[('Operational review', 'We visit the property and review how it runs today: occupancy, rates, staffing, costs and registrations. Then we tell you where we see room to improve.'),
                 ('Proposal', 'You receive a management proposal with the scope, the transition plan and a fee structure that fits the size of the operation.'),
                 ('Transition and operation', 'We set up registrations, listings and systems, then run day-to-day operations and report to you every month.')],
            form_h='Tell us about your property',
            form_p='Share the type of property, the number of units and where it is. We\'ll get back to you to arrange an operational review.',
            form_title='Request a free consultation', form_note='Form not loading?', form_open='Open it in a new tab'),
 'es': dict(slug='es/comercial', home='Inicio', crumb='Comercial',
            title='Administración de hoteles y edificios en Medellín',
            desc='Administración hotelera en Medellín: operamos hoteles y edificios completos para sus dueños, desde la distribución y los precios hasta los informes mensuales.',
            h1='Administración hotelera comercial',
            lead='Hoteles, edificios completos y proyectos de hospitalidad comunitaria en Medellín, operados para sus dueños por el mismo equipo y los mismos sistemas que administran nuestros apartamentos.',
            who_h='Con quién trabajamos',
            who=[('Hoteles y hoteles boutique', 'Hoteles independientes que quieren mejor distribución en línea, precios más inteligentes y un servicio al huésped confiable, sin perder su propia identidad.'),
                 ('Edificios completos', 'Aparthoteles y edificios de unidades amobladas operados como una sola operación: cada unidad con su precio, su aseo, su mantenimiento y sus informes, todo junto.'),
                 ('Hospitalidad comunitaria', 'Coliving, comunidades residenciales y edificios que combinan estadías cortas y largas, donde huéspedes y residentes comparten los mismos espacios.')],
            run_h='Lo que operamos por usted',
            run_lead='Un solo operador para toda la propiedad, con un solo punto de contacto para dueños e inversionistas.',
            run=['Distribución en Airbnb, Booking.com, Expedia y VRBO, con calendarios sincronizados y precios dinámicos',
                 'Atención al huésped 24/7: reservas, check-ins y comunicación con los huéspedes',
                 'Aseo y mantenimiento, coordinados y supervisados',
                 'Zonas comunes, normas de convivencia y relación con los residentes en edificios compartidos',
                 'Registros y reportes de RNT, SIRE y TRA',
                 'Portal del propietario con estados financieros mensuales bajo GAAP'],
            how_h='Cómo asumimos una operación',
            how=[('Revisión operativa', 'Visitamos la propiedad y revisamos cómo funciona hoy: ocupación, tarifas, personal, costos y registros. Luego le decimos dónde vemos oportunidades de mejora.'),
                 ('Propuesta', 'Recibe una propuesta de administración con el alcance, el plan de transición y una estructura de tarifas acorde al tamaño de la operación.'),
                 ('Transición y operación', 'Configuramos registros, anuncios y sistemas, y luego operamos el día a día y le reportamos cada mes.')],
            form_h='Cuéntenos sobre su propiedad',
            form_p='Indíquenos el tipo de propiedad, el número de unidades y dónde está. Nos pondremos en contacto para coordinar una revisión operativa.',
            form_title='Solicite una consulta gratuita', form_note='¿No carga el formulario?', form_open='Ábralo en una pestaña nueva'),
}
for lang in LANGS:
    ui = COMMERCIAL[lang]
    en_url, es_url = SITE + 'commercial/', SITE + 'es/comercial/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    who = ''.join(f'''
      <div class="pain">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icon}</svg>
        <h3>{h}</h3><p>{p}</p></div>''' for icon, (h, p) in zip(COMMERCIAL_ICONS, ui['who']))
    run = ''.join(f'\n        <li>{CHECK}{x}</li>' for x in ui['run'])
    how = ''.join(f'\n      <li><h3>{h}</h3><p>{p}</p></li>' for h, p in ui['how'])
    form = LEAD_FORM + lang
    h = HOME[lang]; i = h.index('<div class="contact-list">')
    contact_list = h[i:h.index('</div>', i) + 6]   # WhatsApp, email and office address, as on the home page
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="commercial-who">
  <div class="wrap">
    <div class="head"><h2>{ui["who_h"]}</h2></div>
    <div class="pains pains-3">{who}
    </div>
  </div>
</section>
<section class="dark commercial-run">
  <div class="wrap">
    <div class="head"><h2>{ui["run_h"]}</h2><p class="lead">{ui["run_lead"]}</p></div>
    <ul class="checks">{run}
    </ul>
  </div>
</section>
<section class="commercial-how">
  <div class="wrap">
    <div class="head"><h2>{ui["how_h"]}</h2></div>
    <ol class="steps">{how}
    </ol>
  </div>
</section>
<section id="contact" class="dark">
  <div class="wrap contact">
    <div>
      <h2>{ui["form_h"]}</h2>
      <p class="lead">{ui["form_p"]}</p>
      {contact_list}
    </div>
    <div class="lead-embed">
      <iframe src="{form}" title="{ui["form_title"]}" loading="lazy"></iframe>
      <p class="form-note">{ui["form_note"]} <a href="{form}" target="_blank" rel="noopener">{ui["form_open"]}</a>.</p>
    </div>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Service', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'serviceType': ui['h1'], 'areaServed': 'Medellín, Colombia', 'provider': provider_ref()},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/comercial/') if lang == 'en' else ('../../commercial/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'commercial/', SITE + 'es/comercial/', TODAY))


# ======================= 4a. Diamond Card venues (opened from the Wallet pass) =======================
# Guests reach it from the "Membership benefits" button / back-field link on the Diamond Card. noindex, not in the
# sitemap, not linked from the menu. Venue data and the confirmed deals live in _build/diamond_card.py.
LINK_ICON = {
    'map': '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    'web': '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    'book': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    'instagram': '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/>',
}
for lang in LANGS:
    ui = DIAMOND[lang]
    en_url, es_url = SITE + 'diamond-card/', SITE + 'es/tarjeta-diamante/'
    url = es_url if lang == 'es' else en_url
    assets = '../assets/' if lang == 'en' else '../../assets/'
    items = []
    # A-Z by name, ignoring accents and case (Ensō, Medellín)
    az = lambda v: unicodedata.normalize('NFKD', v['name']).encode('ascii', 'ignore').decode().lower()
    for v in sorted(VENUES, key=az):
        need = (f'<small class="dc-need dc-need-sin"><a href="{SINMENTE_SIGNUP}" target="_blank" rel="noopener">{ui["sin_line"]}</a></small>'
                if v.get('sinmente') else f'<small class="dc-need">{ui["own_line"]}</small>')
        deal = (f'<p class="dc-deal"><span>{ui["deal"]}</span>{html.escape(v["deal"][lang])}{need}</p>' if v['deal']
                else f'<p class="dc-deal dc-soon">{ui["soon"]}</p>')
        links = ''.join(
            f'<a href="{href}" target="_blank" rel="noopener"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{LINK_ICON[k]}</svg>'
            f'{ui["link"][k]}</a>' for k, href in v['links'])
        items.append(f'''      <li class="dc-venue reveal">
        <div class="dc-logo"><img src="{assets}partners/{v["logo"]}" alt="" style="height:{v["h"]}px" decoding="async"></div>
        <h2>{html.escape(v["name"])}</h2>
        <p class="dc-about">{html.escape(v["about"][lang])}</p>
        {deal}
        <p class="dc-links">{links}</p>
      </li>''')
    wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(ui['wa_text'])
    body = f'''<section class="dc-hero dark">
  <div class="wrap">
    <p class="dc-kicker">{ui["kicker"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="dc-list">
  <div class="wrap">
    <aside class="dc-sin reveal">
      <div>
        <p class="dc-sin-kicker">{ui["sin_kicker"]}</p>
        <h2>{ui["sin_h"]}</h2>
        <p>{ui["sin_p"]}</p>
      </div>
      <a class="btn btn-primary" href="{SINMENTE_SIGNUP}" target="_blank" rel="noopener">{ui["sin_btn"]}</a>
    </aside>
    <ul class="dc-venues" data-stagger>
{chr(10).join(items)}
    </ul>
    <p class="dc-note">{ui["note"]} <a href="{wa}" target="_blank" rel="noopener">{ui["wa"]}</a></p>
  </div>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'publisher': {'@id': business_id()}}]}
    en_href, es_href = (('./', '../es/tarjeta-diamante/') if lang == 'en' else ('../../diamond-card/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema, noindex=True))

# ======================= 4b. Old Wix URLs → redirects, and 404.html =======================
# GitHub Pages has no server-side redirects, so each old path gets a tiny page that redirects instantly
# (meta refresh + JS) and declares the new URL as canonical. Not listed in sitemap.xml.
REDIRECTS = {
    'property-management':            '',            # → home until /long-term-property-management-medellin/ has its copy (it is noindex)
    'contact':                        '#contact',
    'es/contact':                     'es/#contact',
    'es/airbnb-revenue-calculator':   'es/calculadora-ingresos-airbnb-medellin/',   # EN URL is now a real page (4i)
    'es/rentals':                     'es/arriendos/',   # old URL flagged by Bing (Nov 12, 2026)
    'tours-transportation':           'tours/',
    'properties/finca-con-bosque-nativo-privado': 'rentals/',   # any other /properties/* is sent to /rentals/ by 404.html
    'about-us':                       'team/',       # old Wix URL, still used by Google Ads sitelinks
    'real-estate-portfolio':          'rentals/',    # old Wix URL, still used by Google Ads sitelinks
}
for old, new in REDIRECTS.items():
    target = SITE + new
    es_page = old.startswith('es/')
    write(f'{old}/index.html', f'''<!doctype html>
<html lang="{'es' if es_page else 'en'}">
<head>
<meta charset="utf-8">
<title>{'Esta página se trasladó' if es_page else 'This page has moved'} | Medellín Concierge</title>
<link rel="canonical" href="{target}">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace({json.dumps(target)});</script>
</head>
<body>
<p>{'Esta página se trasladó a' if es_page else 'This page has moved to'} <a href="{target}">{target}</a>.</p>
</body>
</html>
''')

def absolute_links(h):
    h = h.replace('href="#top"', 'href="/"')
    h = re.sub(r'href="#(?=[a-z])', 'href="/#', h)
    return re.sub(r'(src|href)="(?!https?:|mailto:|tel:|#|/|data:)', lambda m: f'{m.group(1)}="/', h)

hdr404 = set_switch(absolute_links(en[en.index('<header id="top">'):en.index('</header>') + len('</header>')]), '/', '/es/', 'en')
ftr404 = absolute_links(en[en.index('<footer>'):en.index('</footer>') + len('</footer>')])
page_links = ''.join(f'<a href="/{p["en"]["slug"]}/">{p["en"]["h1"]}</a>' for p in PAGES if p['key'] in ('airbnb', 'long-term', 'colombia') and COMPLETE[p['key']])
page_links_es = ''.join(f'<a href="/es/{p["es"]["slug"]}/">{p["es"]["h1"]}</a>' for p in PAGES if p['key'] in ('airbnb', 'long-term', 'colombia') and COMPLETE[p['key']])
write('404.html', f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | Medellín Concierge</title>
<meta name="robots" content="noindex">
<script>
  // Old Wix property listings (/properties/…): send them to the rental listings.
  if (/^\\/properties\\//.test(location.pathname)) location.replace('/rentals/');
</script>
<link rel="icon" type="image/png" href="/assets/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>

{hdr404}

<main>
<section class="page-top">
  <div class="wrap">
    <h1>Page not found</h1>
    <p class="lead">This page doesn’t exist, or it moved when we launched our new website. <span lang="es">Esta página no existe o se trasladó con nuestro nuevo sitio web.</span></p>
    <div class="ref-ctas" style="margin-top:24px"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-ghost" href="/es/" lang="es">Inicio en español</a></div>
  </div>
</section>
<article class="article">
  <div class="wrap">
    <nav class="more-posts" aria-label="Popular pages">
      <h2>Popular pages</h2>
      <a href="/#plans">Plans and fees</a><a href="/#calculator">Revenue calculator</a>{page_links}<a href="/rentals/">Furnished rentals</a><a href="/blog/">Blog</a><a href="/#contact">Request a free consultation</a>
    </nav>
    <nav class="more-posts" aria-label="Páginas principales" lang="es">
      <h2>Páginas principales</h2>
      <a href="/es/#plans">Planes y tarifas</a><a href="/es/#calculator">Calculadora de ingresos</a>{page_links_es}<a href="/es/arriendos/">Arriendos amoblados</a><a href="/es/blog/">Blog</a><a href="/es/#contact">Solicitar una consulta gratuita</a>
    </nav>
  </div>
</article>
</main>

{ftr404}

<script src="/assets/nav.js"></script>
<script>document.getElementById('yr').textContent = new Date().getFullYear();</script>
</body>
</html>
''')


# ======================= 4e. Blog feeds (/blog/feed.xml, /es/blog/feed.xml) =======================
# RSS 2.0 with each post's full text, so an email service can send every new post to newsletter subscribers
# ("RSS-to-email"). Links inside the post are made absolute so they work in an inbox.
def rss_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime('%a, %d %b %Y 12:00:00 -0500')

def absolute_in_email(h, lang):
    base = SITE + ('es/blog/' if lang == 'es' else 'blog/')
    h = re.sub(r'href="/', f'href="{SITE}', h)
    return re.sub(r'href="(?!https?:|mailto:|tel:|#)([^"]+)"', lambda m: f'href="{base}{m.group(1)}"', h)

for lang in LANGS:
    ui = BLOG_UI[lang]
    blog_url = SITE + ('es/blog/' if lang == 'es' else 'blog/')
    items = ''
    for p in POSTS[:20]:
        t = p[lang]; link = blog_url + p['slug'] + '.html'
        items += (f'  <item>\n    <title>{html.escape(t["title"])}</title>\n    <link>{link}</link>\n    <guid isPermaLink="true">{link}</guid>\n'
                  f'    <pubDate>{rss_date(p["date"])}</pubDate>\n    <description>{html.escape(t["description"])}</description>\n'
                  f'    <content:encoded><![CDATA[{absolute_in_email(t["body"], lang)}]]></content:encoded>\n  </item>\n')
    write(('es/blog' if lang == 'es' else 'blog') + '/feed.xml',
          f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
          f'  <title>{html.escape(ui["blog_title"])}</title>\n  <link>{blog_url}</link>\n  <description>{html.escape(ui["blog_lead"])}</description>\n'
          f'  <language>{"es-co" if lang == "es" else "en"}</language>\n  <atom:link href="{blog_url}feed.xml" rel="self" type="application/rss+xml"/>\n'
          f'  <lastBuildDate>{rss_date(POSTS[0]["date"] if POSTS else TODAY)}</lastBuildDate>\n{items}</channel>\n</rss>\n')


# ======================= 5. sitemap.xml + robots.txt =======================
xml = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
# <lastmod> is the date a page's content last changed, so search engines can trust it and recrawl only what
# changed. _build/lastmod.json keeps a fingerprint and date per URL; a date moves only when the page's HTML
# changes (asset ?v= stamps ignored). Blog posts keep their own published/modified date if that is later.
LASTMOD_FILE = os.path.join(HERE, 'lastmod.json')
lastmods = json.load(open(LASTMOD_FILE)) if os.path.exists(LASTMOD_FILE) else {}
BOOTSTRAP = not lastmods   # no history yet; otherwise a URL seen for the first time is new today
def url_file(u):
    rel = u[len(SITE):]
    return os.path.join(ROOT, rel + 'index.html' if rel == '' or rel.endswith('/') else rel)
def git_date(path):
    r = subprocess.run(['git', 'log', '-1', '--format=%ad', '--date=short', '--', path], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() or TODAY
def content_lastmod(u, given):
    f = url_file(u)
    h = open(f, encoding='utf-8').read()
    # Fingerprint the page's own content (title, description, <main>), not the shared menu and footer, so a
    # menu change does not mark every page as changed.
    parts = re.findall(r'<title>.*?</title>|<meta name="description"[^>]*>|<main\b.*?</main>', h, flags=re.S)
    fp = hashlib.sha1(re.sub(r'\?v=[0-9a-f]+', '', ''.join(parts)).encode()).hexdigest()[:12]
    prev = lastmods.get(u)
    if prev and prev[0] == fp: d = prev[1]
    elif prev: d = TODAY                                        # content changed since the last build
    elif BOOTSTRAP: d = given if given != TODAY else git_date(f)  # first build ever: best guess from git
    else: d = given if given != TODAY else TODAY               # page just went live (e.g. copy finished)
    lastmods[u] = [fp, d]
    return max(d, given) if given != TODAY else d
for en_url, es_url, given in SITEMAP:
    for loc in (en_url, es_url):
        lastmod = content_lastmod(loc, given)
        xml += ['  <url>', f'    <loc>{loc}</loc>', f'    <lastmod>{lastmod}</lastmod>',
                f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>',
                f'    <xhtml:link rel="alternate" hreflang="es" href="{es_url}"/>',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>', '  </url>']
xml.append('</urlset>')
write('sitemap.xml', '\n'.join(xml) + '\n')
live = {u for e, x, _ in SITEMAP for u in (e, x)}
json.dump({u: v for u, v in sorted(lastmods.items()) if u in live}, open(LASTMOD_FILE, 'w'), indent=1)
write('robots.txt', f'User-agent: *\nAllow: /\nDisallow: /_build/\n\nSitemap: {SITE}sitemap.xml\n')

# ======================= 6. llms.txt =======================
# A plain-text map of the site for AI assistants and answer engines (llmstxt.org format): who we are, the key
# facts they get asked about, and every English page with its description. Rebuilt from the pages each build.
def page_meta(u):
    h = open(url_file(u), encoding='utf-8').read()
    t = re.search(r'<title>(.*?)</title>', h, flags=re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', h)
    return (html.unescape(t.group(1)).strip() if t else u), (html.unescape(d.group(1)) if d else '')
B = BUSINESS
llms = [f"# {B['name']}", '',
        f"> {B['legal_name']} is a property management company in Medellín, Colombia, managing Airbnb / short-term "
        f"and long-term rentals for local and foreign owners in El Poblado, Laureles, Envigado and Sabaneta. "
        f"Bilingual team (English and Spanish), office in El Poblado.", '',
        '## Key facts', '',
        f"- Services: {', '.join(B['services_en'])}",
        f"- Areas served: {', '.join(B['area_served'])}",
        '- Fees: Basic plan 12% + IVA of rental income for long stays (30+ nights), 17% + IVA for short stays; '
        'Premium plan 15% + IVA long stays, 20% + IVA short stays. No upfront fees. Premium also pays the owner\'s '
        'property tax, HOA fees, utilities and internet, with a monthly accounting report.',
        f"- Google rating: {B['google_rating']} out of 5 from {B['google_reviews']} Google reviews (checked {B['rating_checked']}; "
        f"profile: {B['map']})",
        f"- Office: {B['street']}, {B['locality']}, {B['region']}, Colombia ({B['map']})",
        f"- Phone / WhatsApp: {B['telephone']}",
        f"- Email: {B['email']}",
        f"- NIT (Colombian tax ID): {B['tax_id']}",
        f"- Website (English): {SITE} | Spanish: {SITE}es/",
        f"- Profiles: {', '.join(SAME_AS)}", '']
# Renters get their own section (backlog R10): a dated summary from the HostFlow feed, then each rentals page with its
# Spanish twin and one factual line (counts and prices as of the feed date), then the renter guides.
RENT_TOP = {SITE + 'rentals/', SITE + 'monthly-rentals-medellin/', SITE + 'short-term-rentals-medellin/'}
RENT_AREA = {SITE + f'rentals/{slug}/': area for area, slug in RA_LIVE}
def rent_fact(u):
    st = rl_stats('en'); a = st['{AS_OF}']
    if u == SITE + 'rentals/':
        return (f"As of {a}: {st['{N_AVAIL}']} furnished apartments and homes with a live price ({st['{N_MONTH}']} by the month, "
                f"{st['{N_SHORT}']} by the night) out of {st['{TOTAL}']} furnished properties we manage; by area: {st['{AREA_COUNTS}']}.")
    if u == SITE + 'monthly-rentals-medellin/':
        return (f"As of {a}: {st['{N_MONTH}']} furnished homes by the month (30+ nights), {st['{MIN_MONTH}']} to {st['{MAX_MONTH}']} COP "
                f"a month; by area: {st['{MONTH_AREA_COUNTS}']}.")
    if u == SITE + 'short-term-rentals-medellin/':
        ss = short_stats('en')[0]
        return (f"As of {a}: {st['{N_SHORT}']} furnished apartments by the night, from {ss['{MIN_NIGHT}']} COP a night; "
                f"by area: {ss['{SHORT_AREA_COUNTS}']}.")
    if u in RENT_AREA:
        area = RENT_AREA[u]; s0, P, month, night = area_stats('en', area)
        parts = ([f"{s0['{N_MONTH}']} by the month ({s0['{MIN_MONTH}']} to {s0['{MAX_MONTH}']} COP a month)"] if month else []) + \
                ([f"{s0['{N_SHORT}']} by the night (from {s0['{MIN_NIGHT}']} COP)"] if night else [])
        return f"As of {a}: {len(P)} furnished homes in {area} with a live price: {' and '.join(parts)}." if parts else ''
    return ''
pages, posts, rent_pages, rent_posts = [], [], [], []
for en_url, es_url, _ in SITEMAP:
    t, d = page_meta(en_url)
    is_post = '/blog/' in en_url and not en_url.endswith('/blog/')
    if en_url in RENT_TOP or en_url in RENT_AREA:
        rent_pages.append(f'- [{t}]({en_url}) (Spanish: {es_url}): {d} {rent_fact(en_url)}'.rstrip())
    elif is_post and en_url.rsplit('/', 1)[-1].removesuffix('.html') in RENTER_GUIDES:
        rent_posts.append(f'- [{t}]({en_url}): {d}')
    else:
        (posts if is_post else pages).append(f'- [{t}]({en_url}): {d}')
_st = rl_stats('en')
rent_intro = [
    '## Furnished rentals (for renters)', '',
    f"Medellín Concierge also rents the furnished apartments it manages directly to guests, by the month (30+ nights) and "
    f"by the night, booked direct. As of {_st['{AS_OF}']} (from our HostFlow listings feed): {_st['{N_MONTH}']} homes "
    f"by the month from {_st['{MIN_MONTH}']} to {_st['{MAX_MONTH}']} COP a month, {_st['{N_SHORT}']} by the night from "
    f"{_st['{MIN_NIGHT}']} COP, plus a one-time cleaning fee ({_st['{MIN_CLEAN}']} to {_st['{MAX_CLEAN}']} COP). "
    f"Areas: {_st['{AREA_COUNTS}']}. To ask or book, email {B['email']} with dates, number of guests, budget and "
    f"preferred area, or WhatsApp {B['telephone']}; we answer in English or Spanish and confirm availability and the "
    f"total price in writing. For nightly stays we manage the RNT, SIRE (foreign guests reported to Migración Colombia) "
    f"and TRA of the properties we manage (as of November 2026); ask us for the apartment's RNT number. Foreigners can "
    f"rent in Colombia (Constitution, Article 100); unfurnished leases usually ask for a Colombian co-signer (fiador), "
    f"so most newcomers start with a furnished apartment booked direct; ask us what the one you like requires. "
    f"General information, not legal advice.", '']
llms += rent_intro + rent_pages + ['', '### Renter guides (blog)', ''] + rent_posts + ['']
llms += ['## Main pages (for property owners)', ''] + pages + ['', '## Owner guides (blog)', ''] + posts + ['',
         '## Optional', '', f'- [Spanish site]({SITE}es/): every page above is also available in Spanish.',
         f'- [Sitemap]({SITE}sitemap.xml)', '']
write('llms.txt', '\n'.join(llms))
print(f'Done. {len(SITEMAP) * 2} URLs in sitemap.xml')
