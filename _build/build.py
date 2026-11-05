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
import datetime, glob, hashlib, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from es_home import HOME_ES, BLOG_UI
from site_config import SITE, BUSINESS, SAME_AS, NEWSLETTER_ENDPOINT
from landing import PAGES, AREAS
from team import TEAM

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
en, _n = re.subn(r'<div class="newsletter" data-newsletter data-endpoint="[^"]*"(?: hidden)?>',
                lambda m: f'<div class="newsletter" data-newsletter data-endpoint="{html.escape(NEWSLETTER_ENDPOINT, quote=True)}"' + ('' if NEWSLETTER_ENDPOINT else ' hidden') + '>', en)
assert _n == 1, 'newsletter block not found in index.html footer'
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
es = es.replace('href="rentals/"', 'href="arriendos/"').replace('href="team/"', 'href="equipo/"')
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
            lead='The people who manage your property and look after your guests in Medellín.',
            cta_h='Talk to our team', cta_p='Get a free consultation, an income estimate and a management proposal.'),
 'es': dict(slug='es/equipo', home='Inicio', crumb='Equipo',
            title='Nuestro equipo | Medellín Concierge',
            desc='Conozca al equipo de Medellín Concierge: quienes cuidan su propiedad, atienden a sus huéspedes y preparan sus estados mensuales en Medellín.',
            h1='Conozca a nuestro equipo',
            lead='Las personas que administran su propiedad y atienden a sus huéspedes en Medellín.',
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
        cards_html += (f'      <article class="member">\n        <div class="member-photo">{photo}</div>\n'
                       f'        <h2>{html.escape(m["name"])}</h2>\n        <p>{html.escape(m["role"][lang])}</p>\n      </article>\n')
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
                         'worksFor': {'@id': business_id()},
                         **({'image': SITE + 'assets/team/' + m['photo'] + '.webp'}
                            if os.path.exists(os.path.join(ROOT, 'assets', 'team', m['photo'] + '.webp')) else {})} for m in TEAM]},
        breadcrumbs([(ui['home'], home_url), (ui['crumb'], url)])]}
    en_href, es_href = (('./', '../es/equipo/') if lang == 'en' else ('../../team/', './'))
    write(f'{ui["slug"]}/index.html', page(lang, title=ui['title'], desc=ui['desc'], en_url=en_url, es_url=es_url,
          en_href=en_href, es_href=es_href, body=body, schema=schema))
SITEMAP.append((SITE + 'team/', SITE + 'es/equipo/', TODAY))


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
