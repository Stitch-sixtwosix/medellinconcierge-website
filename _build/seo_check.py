# SEO check of every built page: one H1, title <= 60, meta 120-160, JSON-LD parses, img alt present,
# internal links resolve, no placeholder text. Run: python3 _build/seo_check.py  (prints only problems).
# Empty alt is reported but correct for decorative images (logo mark, partner logos next to their visible name).
import os,re,json,sys,html
root=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),".."))
pages=[]
for d,_,fs in os.walk(root):
    if '/_build' in d or '/.git' in d or '/team-photos' in d: continue
    for f in fs:
        if f.endswith('.html'): pages.append(os.path.join(d,f))
def resolves(href,page):
    h=href.split('#')[0].split('?')[0]
    if not h: return True
    if h.startswith('/'): p=root+h
    else: p=os.path.join(os.path.dirname(page),h)
    if os.path.isdir(p): return os.path.exists(os.path.join(p,'index.html'))
    return os.path.exists(p) or os.path.exists(p+'.html')
for p in sorted(pages):
    s=open(p,encoding='utf-8').read()
    rel=p[len(root):]
    if 'googlee' in rel: continue
    probs=[]
    redirect='http-equiv="refresh"' in s.lower() or "http-equiv='refresh'" in s.lower()
    noindex='noindex' in s
    h1=len(re.findall(r'<h1[\s>]',s,re.I))
    t=re.search(r'<title>(.*?)</title>',s,re.S)
    t=html.unescape(t.group(1).strip()) if t else ''
    m=re.search(r'<meta name="description" content="([^"]*)"',s)
    m=html.unescape(m.group(1)) if m else ''
    if not redirect:
        if h1!=1: probs.append(f'h1={h1}')
        if len(t)>60: probs.append(f'title {len(t)}: {t}')
        if not(120<=len(m)<=160): probs.append(f'meta {len(m)}')
    for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>',s,re.S):
        try: json.loads(j)
        except Exception as e: probs.append('jsonld '+str(e))
    for img in re.findall(r'<img\b[^>]*>',s,re.I):
        a=re.search(r'\balt="([^"]*)"',img)
        if not a: probs.append('img no alt: '+img[:100])
        elif not a.group(1).strip() and 'aria-hidden' not in img and 'role="presentation"' not in img: probs.append('img empty alt: '+img[:120])
    for h in re.findall(r'href="([^"]+)"',s):
        if h.startswith(('http','mailto:','tel:','#','javascript','data:','//','https://wa')): continue
        if not resolves(h,p): probs.append('broken '+h)
    vis=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S)
    for bad in ['None','[James:','TODO','copy_note']:
        if re.search(r'>[^<]*\b'+re.escape(bad)+r'\b' if bad=='None' else re.escape(bad),vis): probs.append('text '+bad)
    if probs: print(rel, 'noindex' if noindex else '', 'REDIRECT' if redirect else ''); [print('   ',x) for x in sorted(set(probs))]
