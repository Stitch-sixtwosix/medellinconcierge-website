#!/usr/bin/env python3
"""Build medellinconcierge.net (static site, no dependencies).

    python3 _build/build.py

index.html (English home page) is the hand-edited source. This script then:
  1. refreshes index.html: latest blog cards + structured data (business, website, FAQ)
  2. writes es/index.html from index.html + the Spanish strings in es_home.py
  3. writes the blog in both languages from _build/posts/*.json (one file per post)
  4. writes the area / foreign-owner landing pages from landing.py, and the rental listings
     (/rentals/, /es/arriendos/) from listings.json (refresh it with fetch_listings.py)
  5. writes sitemap.xml and robots.txt
It stops with a clear message if an English string in es_home.py no longer exists in index.html.
"""
import datetime, glob, hashlib, html, json, os, re, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from es_home import HOME_ES, BLOG_UI
from site_config import SITE, BUSINESS, SAME_AS
from landing import PAGES, AREAS

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


# ---------------- shared pieces ----------------
def lang_switch(en_href, es_href, current):
    cur = lambda l: ' aria-current="true"' if l == current else ''
    label = 'Idioma' if current == 'es' else 'Language'
    return (f'<div class="lang-switch" role="group" aria-label="{label}">\n'
            f'      <a href="{en_href}" lang="en" hreflang="en" aria-label="English"{cur("en")} data-lang="en">EN</a>'
            f'<a href="{es_href}" lang="es" hreflang="es" aria-label="Español"{cur("es")} data-lang="es">ES</a>\n    </div>')

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
        'name': b['name'], 'legalName': b['legal_name'],
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
         'inLanguage': ['en', 'es'], 'publisher': {'@id': business_id()}},
        faq_schema(s)]}
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

def set_teaser(s, lang):
    s, n = re.subn(r'(<div class="post-grid" data-stagger>\n).*?(    </div>\n    <p class="blog-more)',
                   lambda m: m.group(1) + cards(lang, 'blog/', POSTS[:3]) + m.group(2), s, count=1, flags=re.S)
    assert n == 1, 'blog teaser grid not found'
    return s


# ======================= 1. English home =======================
print('Building…')
en = read('index.html')
en = set_teaser(en, 'en')
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
es = es.replace('href="rentals/"', 'href="arriendos/"')
for pg in PAGES:   # landing page links point to the Spanish versions
    es = es.replace(f'href="{pg["en"]["slug"]}/"', f'href="{pg["es"]["slug"]}/"')
es = set_teaser(es, 'es')
es = set_home_jsonld(es, 'es')
es = re.sub(r"<script>document\.documentElement\.classList\.add\('js'\);.*?</script>",
            "<script>document.documentElement.classList.add('js')</script>", es, count=1, flags=re.S)
es = es.replace(f'<meta property="og:url" content="{SITE}">', f'<meta property="og:url" content="{SITE}es/">')
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
<meta property="og:image" content="{SITE}assets/mark.png">
<meta property="og:image:alt" content="{'Logo de Medellín Concierge' if lang == 'es' else 'Medellín Concierge logo'}">
<meta property="og:site_name" content="Medellín Concierge">
<meta property="og:locale" content="{'es_CO' if lang == 'es' else 'en_US'}">
<meta name="twitter:card" content="summary">
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
      </div>
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
            more_h='More from Medellín Concierge', all_plans='Compare plans in detail',
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
            more_h='Más de Medellín Concierge', all_plans='Comparar los planes en detalle',
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
    for lang in LANGS:
        c = pg[lang]; ui = L[lang]
        incomplete = c['description'] is None or c['intro'] is None or any(b is None for _, b in c['blocks'])
        intro = f'<div class="lead">{c["intro"]}</div>' if c['intro'] else placeholder(lang, pg['key'], 'intro', dark=True)
        blocks = ''.join(f'\n      <h2>{h}</h2>\n      ' + (b if b else placeholder(lang, pg['key'], f'blocks[{i}]'))
                         for i, (h, b) in enumerate(c['blocks']))
        inc = ''.join(f'<li>{CHECK}{x}</li>' for x in ui['inc'])
        more = ''.join(f'<a href="../{o[lang]["slug"]}/">{o[lang]["h1"]}</a>'
                       for o in PAGES if o is not pg)
        home_href = '../'
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="{home_href}">{ui["home"]}</a> / {pg["label"][lang]}</p>
    <h1>{c["h1"]}</h1>
    {intro}
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
      <p>{ui["plans_note"]} <a href="{home_href}#plans">{ui["all_plans"]}</a></p>
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
# Data comes from _build/listings.json, written by fetch_listings.py (Hostflow's public listings feed).
# Hostflow's feed and photos cannot be read from another website in the browser, so the page is static:
# re-run fetch_listings.py + build.py to refresh it. Availability labels are re-checked against today's
# date in the visitor's browser, so "Available from 20 Nov" turns into "Available now" on its own.
R = {
 'en': dict(slug='rentals', home='Home', crumb='Rentals',
            title='Furnished Rentals in Medellín | Medellín Concierge',
            desc='Furnished apartments and homes for short and monthly stays in El Poblado, Laureles, Envigado, Sabaneta and across Medellín, with photos and prices.',
            h1='Furnished rentals in Medellín',
            lead='Apartments and homes we manage, for short and monthly stays. Tap “I’m interested” and we’ll answer you on WhatsApp.',
            updated='Listings updated {date}. Dates and prices can change; we confirm availability when you message us.',
            live='See live availability', f_label='Filter properties', all='All', now='Available now', short='Short stays', month='Monthly stays',
            area_label='Location', any_area='All locations', count1='property', countn='properties', none='No properties match these filters.',
            avail_now='Available now', avail_from='Available from {d}', ask_h='More homes we manage',
            ask_p='These properties have no dates or prices published right now. Ask us about availability.',
            ask_badge='Ask about availability', no_photo='Photos coming soon', interested='I’m interested', book='Book on Airbnb',
            per={'night': 'night', 'month': 'month'}, frm='From', stay={'short_term': 'Short stays', 'long_term': 'Monthly stays'},
            bed=('bedroom', 'bedrooms'), bath=('bath', 'baths'), guests='up to {n} guests', studio='Studio',
            wa='Hi! I’m interested in property {ref} ({title}). Is it available?\n{url}',
            wa_ask='Hi! I’d like to know when property {ref} ({title}) is available.\n{url}',
            amen=dict(ac='Air conditioning', washer='Washer', dryer='Dryer', elevator='Elevator', parking='Parking',
                      gym='Gym', bbq='BBQ', playground='Playground'),
            owners_h='Own a property in Medellín?', owners_p='We manage homes like these for their owners, from listing to monthly GAAP statements.',
            owners_cta='See our management plans'),
 'es': dict(slug='es/arriendos', home='Inicio', crumb='Arriendos',
            title='Arriendos amoblados en Medellín | Medellín Concierge',
            desc='Apartamentos y casas amoblados para estancias cortas y mensuales en El Poblado, Laureles, Envigado, Sabaneta y todo Medellín, con fotos y precios.',
            h1='Arriendos amoblados en Medellín',
            lead='Apartamentos y casas que administramos, para estancias cortas y mensuales. Toque «Me interesa» y le respondemos por WhatsApp.',
            updated='Propiedades actualizadas el {date}. Fechas y precios pueden cambiar; confirmamos la disponibilidad cuando nos escriba.',
            live='Ver disponibilidad en vivo', f_label='Filtrar propiedades', all='Todas', now='Disponibles ya', short='Estancias cortas', month='Estancias mensuales',
            area_label='Ubicación', any_area='Todas las ubicaciones', count1='propiedad', countn='propiedades', none='Ninguna propiedad coincide con estos filtros.',
            avail_now='Disponible ya', avail_from='Disponible desde el {d}', ask_h='Más propiedades que administramos',
            ask_p='Estas propiedades no tienen fechas ni precios publicados en este momento. Pregúntenos por su disponibilidad.',
            ask_badge='Consultar disponibilidad', no_photo='Fotos próximamente', interested='Me interesa', book='Ver en Airbnb',
            per={'night': 'noche', 'month': 'mes'}, frm='Desde', stay={'short_term': 'Estancias cortas', 'long_term': 'Estancias mensuales'},
            bed=('habitación', 'habitaciones'), bath=('baño', 'baños'), guests='hasta {n} huéspedes', studio='Estudio',
            wa='¡Hola! Me interesa la propiedad {ref} ({title}). ¿Está disponible?\n{url}',
            wa_ask='¡Hola! Quisiera saber cuándo está disponible la propiedad {ref} ({title}).\n{url}',
            amen=dict(ac='Aire acondicionado', washer='Lavadora', dryer='Secadora', elevator='Ascensor', parking='Parqueadero',
                      gym='Gimnasio', bbq='BBQ', playground='Parque infantil'),
            owners_h='¿Tiene una propiedad en Medellín?', owners_p='Administramos propiedades como estas para sus dueños, desde la publicación hasta los estados financieros mensuales bajo GAAP.',
            owners_cta='Ver nuestros planes de administración'),
}
HOSTFLOW_LISTINGS = 'https://hostflow.in/listings?t=fv0tM03REiayJ2NegmXX-5RK'
AREA_FIX = {'Medellin': 'Medellín', 'Guatape': 'Guatapé', 'Bogota': 'Bogotá'}
SHORT_MONTHS = {'en': 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(),
                'es': 'ene feb mar abr may jun jul ago sep oct nov dic'.split()}

feed = json.load(open(os.path.join(HERE, 'listings.json'), encoding='utf-8'))
props = feed['properties']
seen = {}
for p in props:
    p['area'] = AREA_FIX.get(p.get('area') or '', p.get('area') or '')
    base = 'p' + re.sub(r'\D', '', p['ref'] or '') or 'p'
    seen[base] = seen.get(base, 0) + 1
    p['_id'] = base if seen[base] == 1 else f'{base}-{seen[base]}'   # the feed has one duplicated ref
    p['_listed'] = bool(p.get('active') and p.get('price') and p['price'].get('amount'))
listed = sorted([p for p in props if p['_listed']], key=lambda p: (max(p.get('available_from') or TODAY, TODAY), p['ref']))
asking = sorted([p for p in props if not p['_listed']], key=lambda p: (not p.get('cover_photo'), p['ref']))   # photos first
areas = sorted({p['area'] for p in listed if p['area']}, key=lambda a: (-sum(1 for p in listed if p['area'] == a), a))

def short_date(iso, lang):
    y, m, d = map(int, iso.split('-'))
    return f'{d} {SHORT_MONTHS[lang][m-1]}' if lang == 'es' else f'{SHORT_MONTHS[lang][m-1]} {d}'

def cop(n): return '$' + f'{int(n):,}'.replace(',', '.') + ' COP'

def plural(n, pair): return f'{n} {pair[0] if n == 1 else pair[1]}'

def listing_card(p, lang, ui, page_url, prefix):
    title = html.escape(p.get(f'title_{lang}') or p.get('title_en') or p['ref'])
    url = f'{page_url}#{p["_id"]}'
    facts = []
    if p.get('bedrooms') == 0: facts.append(ui['studio'])
    elif p.get('bedrooms'): facts.append(plural(p['bedrooms'], ui['bed']))
    if p.get('bathrooms'): facts.append(plural(p['bathrooms'], ui['bath']))
    if p.get('max_guests'): facts.append(ui['guests'].format(n=p['max_guests']))
    amen = ''.join(f'<li>{ui["amen"][a]}</li>' for a in p.get('amenities') or [] if a in ui['amen'])
    if p.get('cover_photo'):
        photo = f'<img src="{prefix}assets/listings/{p["cover_photo"]}.webp" alt="{title}" loading="lazy" decoding="async" width="800" height="534">'
    else:
        photo = f'<span class="no-photo">{ui["no_photo"]}</span>'
    if p['_listed']:
        frm = p.get('available_from') or TODAY
        badge_txt = ui['avail_now'] if frm <= TODAY else ui['avail_from'].format(d=short_date(frm, lang))
        badge = f'<span class="avail{" now" if frm <= TODAY else ""}" data-from="{frm}">{badge_txt}</span>'
        pr = p['price']
        price = (f'<p class="price">{ui["frm"] + " " if pr.get("from") else ""}<strong>{cop(pr["amount"])}</strong> / {ui["per"].get(pr.get("per"), pr.get("per") or "")}</p>')
        wa_text = ui['wa'].format(ref=p['ref'], title=html.unescape(title), url=url)
    else:
        badge = f'<span class="avail ask">{ui["ask_badge"]}</span>'
        price = ''
        wa_text = ui['wa_ask'].format(ref=p['ref'], title=html.unescape(title), url=url)
    wa = 'https://wa.me/573042773864?text=' + urllib.parse.quote(wa_text)
    airbnb = next((b['url'] for b in p.get('booking_links') or [] if b.get('platform') == 'Airbnb' and b.get('url', '').startswith('https://')), None)
    book = f'<a class="btn btn-outline" href="{html.escape(airbnb)}" target="_blank" rel="noopener">{ui["book"]}</a>' if airbnb else ''
    stay = ui['stay'].get(p.get('stay_type') or '')
    meta = ' · '.join(x for x in (p['ref'], stay) if x)
    return f'''      <article class="listing" id="{p["_id"]}" data-stay="{p.get("stay_type") or ""}" data-area="{html.escape(p["area"])}">
        <div class="listing-photo">{photo}{badge}</div>
        <div class="listing-body">
          <p class="listing-meta">{meta}</p>
          <h3>{title}</h3>
          <p class="listing-area">{html.escape(p["area"])}</p>
          {price}<p class="facts">{" · ".join(facts)}</p>
          {f'<ul class="amen">{amen}</ul>' if amen else ''}
          <div class="listing-ctas"><a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">{ui["interested"]}</a>{book}</div>
        </div>
      </article>
'''

for lang in LANGS:
    ui = R[lang]
    en_url, es_url = SITE + R['en']['slug'] + '/', SITE + R['es']['slug'] + '/'
    url = es_url if lang == 'es' else en_url
    prefix = '../' if lang == 'en' else '../../'
    home_url = SITE + ('es/' if lang == 'es' else '')
    opts = ''.join(f'<option value="{html.escape(a)}">{html.escape(a)}</option>' for a in areas)
    grid = ''.join(listing_card(p, lang, ui, url, prefix) for p in listed)
    ask_grid = ''.join(listing_card(p, lang, ui, url, prefix) for p in asking)
    n = len(listed)
    body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / {ui["crumb"]}</p>
    <h1>{ui["h1"]}</h1>
    <p class="lead">{ui["lead"]}</p>
  </div>
</section>
<section class="rentals">
  <div class="wrap">
    <div class="rent-filters" role="group" aria-label="{ui["f_label"]}" hidden>
      <div class="chips">
        <button type="button" class="chip" data-f="all" aria-pressed="true">{ui["all"]}</button><button type="button" class="chip" data-f="now" aria-pressed="false">{ui["now"]}</button><button type="button" class="chip" data-f="short_term" aria-pressed="false">{ui["short"]}</button><button type="button" class="chip" data-f="long_term" aria-pressed="false">{ui["month"]}</button>
      </div>
      <label class="area-pick"><span class="sr-only">{ui["area_label"]}</span><select id="areaPick"><option value="">{ui["any_area"]}</option>{opts}</select></label>
    </div>
    <p class="rent-count" aria-live="polite" data-one="{ui["count1"]}" data-many="{ui["countn"]}">{n} {ui["countn"] if n != 1 else ui["count1"]}</p>
    <div class="listing-grid" id="listingGrid">
{grid}    </div>
    <p class="rent-none" id="rentNone" hidden>{ui["none"]}</p>
    <p class="rent-updated">{ui["updated"].format(date=human_date(feed.get("fetched", TODAY), lang))} <a href="{HOSTFLOW_LISTINGS}" target="_blank" rel="noopener">{ui["live"]}</a></p>
  </div>
</section>
<section class="rentals rentals-ask">
  <div class="wrap">
    <h2>{ui["ask_h"]}</h2>
    <p class="lead">{ui["ask_p"]}</p>
    <div class="listing-grid compact">
{ask_grid}    </div>
    <aside class="article-cta">
      <h2>{ui["owners_h"]}</h2>
      <p>{ui["owners_p"]}</p>
      <div class="ref-ctas"><a class="btn btn-primary" href="../#plans">{ui["owners_cta"]}</a><a class="btn btn-outline" href="../#contact">{L[lang]["cta_1"]}</a></div>
    </aside>
  </div>
</section>
<script>
(() => {{
  // Availability labels follow today's date; filters work on the listed (dated, priced) properties
  const today = new Date().toISOString().slice(0, 10), lang = document.documentElement.lang;
  const mon = {json.dumps(SHORT_MONTHS[lang])}, nowTxt = {json.dumps(ui["avail_now"])}, fromTxt = {json.dumps(ui["avail_from"])};
  document.querySelectorAll('.avail[data-from]').forEach(b => {{
    const f = b.dataset.from, now = f <= today;
    b.classList.toggle('now', now);
    const [y, m, d] = f.split('-').map(Number);
    b.textContent = now ? nowTxt : fromTxt.replace('{{d}}', lang === 'es' ? d + ' ' + mon[m-1] : mon[m-1] + ' ' + d);
  }});
  const box = document.querySelector('.rent-filters'), grid = document.getElementById('listingGrid'), pick = document.getElementById('areaPick');
  const count = document.querySelector('.rent-count'), none = document.getElementById('rentNone');
  let f = 'all'; box.hidden = false;
  const apply = () => {{
    let n = 0;
    grid.querySelectorAll('.listing').forEach(c => {{
      const badge = c.querySelector('.avail');
      const ok = (f === 'all' || (f === 'now' ? badge.classList.contains('now') : c.dataset.stay === f)) && (!pick.value || c.dataset.area === pick.value);
      c.hidden = !ok; if (ok) n++;
    }});
    count.textContent = n + ' ' + (n === 1 ? count.dataset.one : count.dataset.many);
    none.hidden = n > 0;
  }};
  box.querySelectorAll('.chip').forEach(b => b.addEventListener('click', () => {{
    f = b.dataset.f; box.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', x === b));
    apply();
  }}));
  pick.addEventListener('change', apply);
}})();
</script>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': ui['h1'], 'description': ui['desc'], 'url': url, 'inLanguage': lang,
         'publisher': {'@id': business_id()}},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/arriendos/') if lang == 'en' else ('../../rentals/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'rentals/', SITE + 'es/arriendos/', feed.get('fetched', TODAY)))
print(f'  rentals: {len(listed)} listed, {len(asking)} "ask about availability" (data from {feed.get("fetched")})')


# ======================= 4b. Old Wix URLs → redirects, and 404.html =======================
# GitHub Pages has no server-side redirects, so each old path gets a tiny page that redirects instantly
# (meta refresh + JS) and declares the new URL as canonical. Not listed in sitemap.xml.
REDIRECTS = {
    'property-management':            '',            # → home until /long-term-property-management-medellin/ has its copy (it is noindex)
    'contact':                        '#contact',
    'es/contact':                     'es/#contact',
    'airbnb-revenue-calculator':      '#calculator',
    'es/airbnb-revenue-calculator':   'es/#calculator',
    'tours-transportation':           '',
    'diamond-card':                   '',
    'properties/finca-con-bosque-nativo-privado': 'rentals/',   # any other /properties/* is sent to /rentals/ by 404.html
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
page_links = ''.join(f'<a href="/{p["en"]["slug"]}/">{p["en"]["h1"]}</a>' for p in PAGES if p['key'] in ('airbnb', 'long-term', 'colombia'))
page_links_es = ''.join(f'<a href="/es/{p["es"]["slug"]}/">{p["es"]["h1"]}</a>' for p in PAGES if p['key'] in ('airbnb', 'long-term', 'colombia'))
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


# ======================= 5. sitemap.xml + robots.txt =======================
xml = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
for en_url, es_url, lastmod in SITEMAP:
    for loc in (en_url, es_url):
        xml += ['  <url>', f'    <loc>{loc}</loc>', f'    <lastmod>{lastmod}</lastmod>',
                f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>',
                f'    <xhtml:link rel="alternate" hreflang="es" href="{es_url}"/>',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>', '  </url>']
xml.append('</urlset>')
write('sitemap.xml', '\n'.join(xml) + '\n')
write('robots.txt', f'User-agent: *\nAllow: /\nDisallow: /_build/\n\nSitemap: {SITE}sitemap.xml\n')
print(f'Done. {len(SITEMAP) * 2} URLs in sitemap.xml')
