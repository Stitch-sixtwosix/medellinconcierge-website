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
import datetime, glob, hashlib, html, json, os, re, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from es_home import HOME_ES, BLOG_UI
from site_config import SITE, BUSINESS, SAME_AS, NEWSLETTER_ENDPOINT
from landing import PAGES, AREAS
from team import TEAM
from faq import FAQ
from fees import FEES
from diamond_card import VENUES, DIAMOND

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
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))).strip()


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
assert f"<strong>{BUSINESS['google_rating']}</strong> on Google · {BUSINESS['google_reviews']} reviews" in en, \
    'index.html hero rating no longer matches google_rating / google_reviews in site_config.py: update the hero line'
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
es = es.replace('href="rentals/"', 'href="arriendos/"').replace('href="team/"', 'href="equipo/"').replace('href="faq/"', 'href="preguntas-frecuentes/"').replace('href="commercial/"', 'href="comercial/"')
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


# ======================= 3. Blog =======================
for lang in LANGS:
    ui = BLOG_UI[lang]
    folder = 'blog' if lang == 'en' else 'es/blog'
    home_url = SITE + ('es/' if lang == 'es' else '')
    blog_url = {'en': SITE + 'blog/', 'es': SITE + 'es/blog/'}
    other = '../es/blog/' if lang == 'en' else '../../blog/'
    sw = lambda slug='': ((f'./{slug}', f'{other}{slug}') if lang == 'en' else (f'{other}{slug}', f'./{slug}'))

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
        # Posts about Airbnb link to the Airbnb management money page (unless the post already does).
        airbnb_pg = next(o for o in PAGES if o['key'] == 'airbnb')[lang]
        related = ''
        if COMPLETE['airbnb'] and 'airbnb' in t['body'].lower() and airbnb_pg['slug'] not in t['body']:
            related = (f'\n      <p>{"Related" if lang == "en" else "Relacionado"}: '
                       f'<a href="../{airbnb_pg["slug"]}/">{airbnb_pg["h1"]}</a></p>')
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
    </div>
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
        write(f'{folder}/{slug}', page(lang, title=t.get('seo_title') or f'{t["title"]} | Medellín Concierge', desc=t['description'],
              en_url=blog_url['en'] + slug, es_url=blog_url['es'] + slug, en_href=en_href, es_href=es_href,
              body=body, schema=schema, og_type='article'))
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
             'provider': {'@id': business_id()},
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
            title='Furnished Rentals in Medellín | Medellín Concierge',
            desc='Furnished apartments and homes for short and monthly stays in El Poblado, Laureles, Envigado, Sabaneta and across Medellín, with photos and prices.',
            h1='Furnished rentals in Medellín',
            lead='Apartments and homes we manage, for short and monthly stays, with live availability. Tap “I’m interested” and we’ll answer you on WhatsApp.',
            frame_title='Medellín Concierge properties', fallback='Not loading?', fallback_link='Open our listings in a new tab',
            owners_h='Own a property in Medellín?', owners_p='We manage homes like these for their owners, from listing to monthly GAAP statements.',
            owners_cta='See our management plans'),
 'es': dict(slug='es/arriendos', home='Inicio', crumb='Arriendos',
            title='Arriendos amoblados en Medellín | Medellín Concierge',
            desc='Apartamentos y casas amoblados para estancias cortas y mensuales en El Poblado, Laureles, Envigado, Sabaneta y todo Medellín, con fotos y precios.',
            h1='Arriendos amoblados en Medellín',
            lead='Apartamentos y casas que administramos, para estancias cortas y mensuales, con disponibilidad en vivo. Toque «Me interesa» y le respondemos por WhatsApp.',
            frame_title='Propiedades de Medellín Concierge', fallback='¿No carga?', fallback_link='Abra nuestras propiedades en una pestaña nueva',
            owners_h='¿Tiene una propiedad en Medellín?', owners_p='Administramos propiedades como estas para sus dueños, desde la publicación hasta los estados financieros mensuales bajo GAAP.',
            owners_cta='Ver nuestros planes de administración'),
}

for lang in LANGS:
    ui = R[lang]
    en_url, es_url = SITE + R['en']['slug'] + '/', SITE + R['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    home_url = SITE + ('es/' if lang == 'es' else '')
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="rentals">
  <div class="wrap">
    <div class="listings-embed">
      <iframe id="mc-listings" src="{HOSTFLOW_LISTINGS}" title="{ui["frame_title"]}" loading="lazy" style="width:100%;min-height:900px;border:0;display:block" allow="clipboard-write"></iframe>
    </div>
    <p class="rent-updated">{ui["fallback"]} <a href="{HOSTFLOW_LISTINGS}" target="_blank" rel="noopener">{ui["fallback_link"]}</a></p>
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
         'publisher': {'@id': business_id()}},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/arriendos/') if lang == 'en' else ('../../rentals/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'rentals/', SITE + 'es/arriendos/', TODAY))


# ======================= 4d. Meet the team (/team/, /es/equipo/) =======================
# People and roles are in team.py; photos (on white, 4:5) in assets/team/, made by team_photos.py.
T = {
 'en': dict(slug='team', home='Home', crumb='Team',
            title='Meet the Team | Medellín Concierge',
            desc='Meet the Medellín Concierge team: the managers who look after your property, your guests and your monthly statements in Medellín, Colombia.',
            h1='Meet the team',
            lead='The people who manage your property, look after your guests and keep your accounts in order in Medellín.',
            cta_h='Talk to our team', cta_p='Get a free consultation, an income estimate and a management proposal.'),
 'es': dict(slug='es/equipo', home='Inicio', crumb='Equipo',
            title='Nuestro equipo | Medellín Concierge',
            desc='Conozca al equipo de Medellín Concierge: quienes cuidan su propiedad, atienden a sus huéspedes y preparan sus estados mensuales en Medellín.',
            h1='Conozca a nuestro equipo',
            lead='Las personas que administran su propiedad, atienden a sus huéspedes y llevan sus cuentas en orden en Medellín.',
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
            h1='Frequently asked questions', lead='Straight answers about how we manage your property in Medellín.',
            cta_h='Still have a question?', cta_p='Write to us or book a free consultation. We reply in English or Spanish.'),
 'es': dict(slug='es/preguntas-frecuentes', home='Inicio', crumb='Preguntas frecuentes',
            title='Preguntas frecuentes | Medellín Concierge',
            desc='Respuestas a las preguntas de los propietarios sobre nuestra administración de Airbnb y rentas largas en Medellín: servicios, tarifas, pagos y RNT.',
            h1='Preguntas frecuentes', lead='Respuestas claras sobre cómo administramos su propiedad en Medellín.',
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
         'provider': {'@id': business_id()}, 'areaServed': {'@type': 'Place', 'name': 'Medellín'}},
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
            desc='Commercial hospitality management in Medellín: we run hotels, full buildings and community hospitality operations for their owners, from distribution and pricing to guests, compliance and monthly reporting.',
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
            title='Administración de hoteles y edificios en Medellín | Medellín Concierge',
            desc='Administración hotelera comercial en Medellín: operamos hoteles, edificios completos y proyectos de hospitalidad comunitaria para sus dueños, desde la distribución y los precios hasta los huéspedes, el cumplimiento legal y los informes mensuales.',
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
         'serviceType': ui['h1'], 'areaServed': 'Medellín, Colombia', 'provider': {'@id': business_id()}},
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
    for v in VENUES:
        deal = (f'<p class="dc-deal"><span>{ui["deal"]}</span>{html.escape(v["deal"][lang])}</p>' if v['deal']
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
    'airbnb-revenue-calculator':      '#calculator',
    'es/airbnb-revenue-calculator':   'es/#calculator',
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
    else: d = given if given != TODAY else git_date(f)          # first time this URL is seen
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
pages, posts = [], []
for en_url, es_url, _ in SITEMAP:
    t, d = page_meta(en_url)
    (posts if '/blog/' in en_url and not en_url.endswith('/blog/') else pages).append(f'- [{t}]({en_url}): {d}')
llms += ['## Main pages', ''] + pages + ['', '## Owner guides (blog)', ''] + posts + ['',
         '## Optional', '', f'- [Spanish site]({SITE}es/): every page above is also available in Spanish.',
         f'- [Sitemap]({SITE}sitemap.xml)', '']
write('llms.txt', '\n'.join(llms))
print(f'Done. {len(SITEMAP) * 2} URLs in sitemap.xml')
