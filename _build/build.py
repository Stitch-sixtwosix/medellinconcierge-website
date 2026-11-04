#!/usr/bin/env python3
"""Build the Spanish site and the blog pages for medellinconcierge.net.

    python3 _build/build.py

index.html (English home page) is the source of truth. This script:
  1. refreshes the blog cards on index.html from posts_en.py
  2. writes es/index.html: index.html with every string in es_home.py swapped to Spanish
  3. writes blog/ and es/blog/ (index + one page per post) using the matching home page's header and footer
It stops with a message if an English string in es_home.py can no longer be found in index.html.
"""
import html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from es_home import HOME_ES, BLOG_UI
from posts_en import POSTS_EN
from posts_es import POSTS_ES

SITE = 'https://www.medellinconcierge.net/'
POSTS = {'en': POSTS_EN, 'es': POSTS_ES}
ARROW = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
def write(p, s):
    full = os.path.join(ROOT, p); os.makedirs(os.path.dirname(full), exist_ok=True)
    old = open(full, encoding='utf-8').read() if os.path.exists(full) else None
    if old != s:
        open(full, 'w', encoding='utf-8').write(s); print('  wrote', p)


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

def alternates(en_url, es_url, canonical):
    return (f'<link rel="canonical" href="{canonical}">\n'
            f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
            f'<link rel="alternate" hreflang="es" href="{es_url}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{en_url}">')

def set_alternates(s, en_url, es_url, canonical):
    s, n = re.subn(r'<link rel="canonical"[^>]*>\n<link rel="alternate" hreflang="en"[^>]*>\n<link rel="alternate" hreflang="es"[^>]*>\n<link rel="alternate" hreflang="x-default"[^>]*>',
                   lambda m: alternates(en_url, es_url, canonical), s, count=1)
    assert n == 1, 'canonical/hreflang block not found'
    return s


def cards(lang, prefix, reveal=True):
    ui = BLOG_UI[lang]; r = ' reveal' if reveal else ''
    out = ''
    for p in POSTS[lang]:
        out += (f'      <a class="post-card{r}" href="{prefix}{p["slug"]}.html">\n'
                f'        <p class="post-meta"><time datetime="{p["date"]}">{p["date_h"]}</time> · {p["mins"]} {ui["min_read"]}</p>\n'
                f'        <h3>{p["title"]}</h3>\n'
                f'        <p>{p["excerpt"]}</p>\n'
                f'        <span class="read">{ui["read"]} {ARROW}</span>\n'
                f'      </a>\n')
    return out

def set_teaser(s, lang):
    s, n = re.subn(r'(<div class="post-grid" data-stagger>\n).*?(    </div>\n    <p class="blog-more)',
                   lambda m: m.group(1) + cards(lang, 'blog/') + m.group(2), s, count=1, flags=re.S)
    assert n == 1, 'blog teaser grid not found'
    return s


# ---------------- 1. English home page: refresh blog cards ----------------
print('Building…')
en = set_teaser(read('index.html'), 'en')
write('index.html', en)

# ---------------- 2. Spanish home page ----------------
es = en
missing = [a for a, b in HOME_ES if a not in es]
if missing:
    sys.exit('These English strings in _build/es_home.py are no longer in index.html. Update es_home.py:\n  - '
             + '\n  - '.join(m[:100] for m in missing))
for a, b in HOME_ES:
    es = es.replace(a, b)
es = set_teaser(es, 'es')
# no auto-redirect on the Spanish page; mark the locale
es = re.sub(r"<script>document\.documentElement\.classList\.add\('js'\);.*?</script>",
            "<script>document.documentElement.classList.add('js')</script>", es, count=1, flags=re.S)
es = es.replace(f'<meta property="og:url" content="{SITE}">', f'<meta property="og:url" content="{SITE}es/">\n<meta property="og:locale" content="es_CO">')
es = set_alternates(es, SITE, SITE + 'es/', SITE + 'es/')
es = set_switch(es, '../', './', 'es')
es = es.replace('src="assets/', 'src="../assets/').replace('href="assets/', 'href="../assets/')
write('es/index.html', es)

# warn about anything that still looks English in the Spanish page's visible text
text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', es, flags=re.S)
text = re.sub(r'<[^>]+>', '\n', text)
eng = [t.strip() for t in text.split('\n') if re.search(r"\b(the|and|your|our|we|you|with|for)\b", t.strip()) and len(t.strip()) > 3]
if eng:
    print('  check these lines on es/index.html, they may still be English:'); [print('    ·', t[:90]) for t in eng[:15]]


# ---------------- 3. Blog pages (EN + ES) ----------------
def chrome(home, depth_prefix):
    """Header, footer and WhatsApp button from a home page, relinked for a page one folder deeper."""
    hdr = home[home.index('<header id="top">'):home.index('</header>') + len('</header>')]
    ftr = home[home.index('<footer>'):home.index('</footer>') + len('</footer>')]
    i = home.index('<a class="wa-float"'); wa = home[i:home.index('</a>', i) + 4]
    def rel(h):
        h = h.replace('href="#top"', 'href="../"')
        h = re.sub(r'href="#(?=[a-z])', 'href="../#', h)
        h = h.replace('href="blog/"', 'href="./"')
        h = re.sub(r'(src|href)="(?!https?:|mailto:|#|\.\./#|\./"|\.\./"|data:)', lambda m: f'{m.group(1)}="{depth_prefix}', h)
        return h
    return rel(hdr), rel(ftr), rel(wa)

def page(lang, title, desc, en_url, es_url, hdr, ftr, wa, body, assets):
    locale = '<meta property="og:locale" content="es_CO">\n' if lang == 'es' else ''
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
{alternates(en_url, es_url, es_url if lang == 'es' else en_url)}
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
{locale}<meta property="og:image" content="{SITE}assets/mark.png">
<link rel="icon" type="image/png" href="{assets}favicon.png">
<link rel="apple-touch-icon" href="{assets}apple-touch-icon.png">
<meta name="theme-color" content="#272727">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{assets}site.css">
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

for lang, home, folder, prefix, assets in (('en', en, 'blog', '../', '../assets/'), ('es', es, 'es/blog', '../', '../../assets/')):
    ui = BLOG_UI[lang]
    hdr, ftr, wa = chrome(home, prefix)
    other = '../es/blog/' if lang == 'en' else '../../blog/'   # path to the same page in the other language
    # blog index
    sw = (lambda h, slug='': set_switch(h, f'./{slug}' if lang == 'en' else f'{other}{slug}', f'{other}{slug}' if lang == 'en' else f'./{slug}', lang))
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
{cards(lang, '', reveal=False).replace('<h3>', '<h2>').replace('</h3>', '</h2>')}    </div>
  </div>
</section>'''
    write(f'{folder}/index.html', page(lang, ui['blog_meta_title'], ui['blog_meta_desc'], SITE + 'blog/', SITE + 'es/blog/', sw(hdr), ftr, wa, body, assets))
    # posts
    for p in POSTS[lang]:
        others = ''.join(f'<a href="{o["slug"]}.html">{o["title"]}</a>' for o in POSTS[lang] if o is not p)
        body = f'''<section class="page-top">
  <div class="wrap">
    <p class="crumbs"><a href="../">{ui["home"]}</a> / <a href="./">{ui["blog"]}</a></p>
    <h1>{p["title"]}</h1>
    <p class="post-meta" style="color:var(--on-dark)"><time datetime="{p["date"]}">{p["date_h"]}</time> · {p["mins"]} {ui["min_read"]} · Medellín Concierge</p>
  </div>
</section>
<article class="article">
  <div class="wrap">
    <div class="prose">
{p["body"].strip()}
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
        slug = p['slug'] + '.html'
        write(f'{folder}/{slug}', page(lang, f'{p["title"]} | Medellín Concierge', html.escape(p['excerpt'], quote=True),
                                       f'{SITE}blog/{slug}', f'{SITE}es/blog/{slug}', sw(hdr, slug), ftr, wa, body, assets))
print('Done.')
