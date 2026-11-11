# How this site is built

Static HTML on GitHub Pages. No framework, no dependencies: just Python 3.

```
python3 _build/build.py
```

Run it after any change below, check the result locally, then commit. **Nothing is published until the
change is pushed to the `main` branch on GitHub, and nothing gets pushed without James's OK.**

| What you want to change | Edit this | Then |
|---|---|---|
| English home page text | `index.html` (hand-edited) | add/adjust the matching Spanish line in `_build/es_home.py` |
| Spanish home page text | `_build/es_home.py` | — |
| A blog post (add or edit) | `_build/posts/YYYY-MM-DD-slug.json` | — |
| Area / foreign-owner landing pages | `_build/landing.py` | — |
| Business facts in structured data | `_build/site_config.py` | — |
| Rental listings (`/rentals/`, `/es/arriendos/`) | nothing: live Hostflow embed | — |
| Meet the team (`/team/`, `/es/equipo/`) | `_build/team.py` (names, roles) | new photo: put it in `team-photos/`, run `python3 _build/team_photos.py` |
| Styles | `assets/site.css` | — |

The build writes `es/`, `blog/`, `es/blog/`, the landing page folders, `rentals/`, `es/arriendos/`, `sitemap.xml` and `robots.txt`.

**Rental listings** (`/rentals/`, `/es/arriendos/`) embed James's live Hostflow listings page, so they update
themselves whenever Hostflow changes; nothing to rebuild.
Never edit those generated files by hand; your change would be overwritten.

## Adding a team member

1. Save the photo in `team-photos/` (in the website folder; it is never published), named like `firstname-lastname.jpg`.
2. Add the person to `_build/team.py` with the same `photo` name and their role in English and Spanish.
3. Run `python3 _build/team_photos.py && python3 _build/build.py`. The photo is cut out onto pure white and framed
   as a 4:5 portrait automatically (macOS only). Until a photo exists, the card shows the person's initials.

## For Sol: adding a blog post (bilingual)

Create one file per post in `_build/posts/`, named `YYYY-MM-DD-slug.json`:

```json
{
 "slug": "short-english-slug",
 "date": "2026-11-05",
 "en": {
  "title": "Article title as shown on the page",
  "seo_title": "Title for Google, max 60 characters",
  "description": "Meta description and card text, 120–155 characters.",
  "minutes": 4,
  "body": "<p>First paragraph…</p>\n<h2>Section</h2>\n<p>…</p>"
 },
 "es": {
  "title": "…", "seo_title": "…", "description": "…", "minutes": 4, "body": "…"
 }
}
```

- Both `en` and `es` are required; the build stops if a field is empty.
- `body` is simple HTML: `<p>`, `<h2>`, `<ul>/<li>`, `<strong>`, `<a href="…">`, `<table>`. No `<h1>` (the title is the H1).
- The same `slug` is used for both languages: `/blog/slug.html` and `/es/blog/slug.html`.
- Optional `"modified": "YYYY-MM-DD"` at the top level when you update an old post.
- The newest three posts appear on the home page automatically; the sitemap updates itself.
- Only facts James has confirmed. No invented numbers, clients, reviews or prices.

## For Lupa: landing page copy

Open `_build/landing.py`. Every `None` is a slot waiting for your text (English under `en`, Spanish under `es`):
`description` (120–155 characters), `intro`, and the body of each `blocks` heading.
While any slot on a page is still `None`, that page shows a dashed placeholder box, is marked `noindex`
and is left out of `sitemap.xml`. Once all slots are filled, the page becomes indexable automatically.

## For James: placeholders that need you

- `_build/site_config.py` → `TODO_SAME_AS`: Google Business Profile (full URL). (Instagram, Facebook and LinkedIn are already in `SAME_AS` and in the footer of `index.html`.)
  Paste each real URL there and move it into `SAME_AS`; only then is it published in the structured data.
- Booking.com, Expedia and VRBO listing links (logo tiles on the home page, marked `data-todo`).

## Publishing (and unattended runs)

- Repo `Stitch-sixtwosix/medellinconcierge-website`. GitHub Pages serves branch `main`, folder `/`.
  **Every push to `main` is a live publish** (about 1 minute).
- Always start with `git pull --rebase origin main`. GitHub sometimes adds its own "Create CNAME"
  commits, and a push without pulling first is rejected.
- Order: edit sources → `python3 _build/build.py` → **stop if it exits non-zero** → commit everything it
  wrote → push. A scheduled job must never push after a failed build.
- **After every publish**, once the GitHub Pages deploy has finished: `python3 _build/after_deploy.py`.
  It checks that every page in the live sitemap can be indexed (HTTP 200, no noindex, canonical to itself,
  EN/ES hreflang, robots.txt allows crawling) and then sends the pages changed today to IndexNow (Bing,
  Yandex, Seznam, Naver). If it reports a problem, fix it before anything else. Google takes no pings: it
  rereads `sitemap.xml`, so the `<lastmod>` dates must be true. The build keeps them true by itself
  (`_build/lastmod.json` remembers each page's content fingerprint; a date moves only when the page's own
  content changes). Never edit `lastmod.json` by hand, and never delete the IndexNow key file
  (`<key>.txt` at the site root, key in `site_config.py`).
- Set `git config user.name` / `user.email` in this repo so automated commits are identifiable.
- Recommended for the first week: have the job send James a summary (or open a pull request) instead of
  pushing directly.
