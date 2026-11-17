# SEO and AI-search backlog

The **Lupa · ship** cloud routine works through this list on its own. On each run it takes the top `todo` item, ships it to the site, and moves it to Done with the date and commit. Anyone can add items. Highest value goes first.

Goal (James, Nov 11 2026): #1 on Google, and named by AI answers (Google AI Overviews, ChatGPT, Perplexity, Gemini, Copilot), for property management / Airbnb management in Medellín and Colombia, in English and Spanish.

## What we know (Nov 11–12, 2026)
- **Bing Webmaster Tools** (signed in as contact@, Nov 12): 106 impressions and 6 clicks in 3 months. Copilot cited us 27 times in Aug 2026 and 0 times since. Bing recommends more links from quality sites and fixing thin pages (item below). Bing is now in scope; it feeds ChatGPT search.
- **Bing live ranks (Nov 12, US English / CO Spanish):** "property management medellin" #2 (behind medellinadvisors.com); "administración de propiedades medellín" #3; "airbnb management medellin" not in top 16 (medellinadvisors.com "Airbnb Management in Medellín: Best Complete 2026 Guide" is #1, then medellin.group, wehostcolombia.com, samba.com.co, everyplace.co, Casacol); "administración airbnb medellín" not in top 8 (oasisliving.co, jefersoncortes.com, findhomecolombia.com, renteo.com.co); "property management colombia" not in top 4 (gutierrezgroup.com.co, ensun, everyplace.co). IndexNow accepted all 176 URLs on Nov 12; Bing reports lag ~4 days.
- **Google, English:**
  - Airbnb management medellin: #5
  - vacation rental management: #2
  - medellin property management: #9
  - best property management company medellin airbnb: #3
  - The AI Overview for "best property management company medellin airbnb" names us third, after Oasis Living (5.0, 23 reviews) and Casacol (4.2, 20 reviews).
- **Google, Spanish:** we are weak. We are not in the top 20 for "administración de airbnb medellín", "administración de propiedades medellín" or "mejor empresa administración airbnb medellín". The top results there are renteo.com.co, medellinbnb.com, myhomekiz.com, elevaremedellin.com, everyplace.co, oasisliving.co and miairbnb.com.
- **Perplexity** does not mention us. It recommends Casacol, Modupe and Medellin Advisors. Its sources are:
  - third-party "top companies" lists (airroi.com, airbtics.com);
  - competitors' answer-style pages: medellinadvisors.com "property-management-fees-in-medellin" and "property-management-medellin-foreign-owners", casacol.co, findhomecolombia.com, everyplace.co.
- **Lesson:** AI engines quote pages that answer one question directly, with concrete numbers, in the first lines.

## Rules for every item
- Only use facts already on the site, in `_build/site_config.py`, or from a cited reputable source.
- Never invent statistics, client numbers, results, reviews or testimonials.
- Fees are exactly as shown on the home page.
- Lead each page with an answer-first summary of 2–3 sentences.
- Every page in both English and Spanish. Spanish is written natively for Colombian owners, not translated word for word.

## Todo
0. **Area pages follow-up:** all four area pages are live (Sabaneta Nov 15). Remaining for El Poblado: the office report's local facts (Comuna 14, Metro Línea A Poblado station, Feria de las Flores, Ley 142 estrato 5/6 surcharge) were left out because medellin.gov.co and wikipedia were unreachable from the cloud session on Nov 13; add them with a cited link once a source can be opened. (Nov 15: metrodemedellin.gov.co, bluradio.com and elpais.com.co were also unreachable from the cloud session.)
1. **Spanish money pages:**
   - Strengthen `/es/` (administración de propiedades Medellín): title, meta, answer-first lead, owner section and FAQ shipped Nov 13; remaining: links from every Spanish blog body (Sol's lane; office report mc-2026-11-16 proposes links in /es/blog/medellin-property-management-guide.html for Sol). /team/ and /faq/ links shipped Nov 16 (office report mc-2026-11-13-build). (`/es/administracion-de-airbnb-medellin/` got keyword-first intro, owner sections and FAQ on Nov 12; remaining for it: links from Spanish blog bodies are Sol's lane.)
   - Use the exact keyword in the title, H1 and first sentence.
   - Add 300–500 words of native Spanish copy for owners: RNT, building rules, payouts in pesos or dollars, reports. Only use facts the site already states.
   - Add an FAQ block with FAQPage schema.
   - Add internal links from every Spanish blog post.
6. **Comparison guide** (Nov 17: skipped for now, it would duplicate Sol's live post /blog/how-to-choose-a-property-manager-in-medellin.html; better as a comparison checklist table added to that post, Sol's lane, or a distinct angle): "How to compare property management companies in Medellín", with a checklist table: fees, payout timing, reporting, licensing, contract length, references.
   - Neutral and useful. Never name or disparage competitors.
7. **Internal linking pass:**
   - Every blog post links to its matching money page (Airbnb, long-term, Colombia, fees).
   - The home page links to the 3 strongest guides.
   - The blog index links to the landing pages.
8. **Technical pass:**
   - All images have descriptive alt text in the page's language.
   - Large images are compressed or resized.
   - No broken internal links (check every built page).
   - Each page has exactly one H1, and titles are 60 characters or fewer.
9. **Long-term rentals page, Spanish keywords:** "administración de arriendos Medellín", "inmobiliaria para arrendar apartamento Medellín", "empresas de arrendamiento Medellín". Strengthen `/es/administracion-de-rentas-largas-medellin/`.

10. **Thin pages flagged by Bing (Nov 12, 2026):** /rentals/ part shipped Nov 17. Remaining: /airbnb-revenue-calculator/ (with /es/airbnb-revenue-calculator/), currently a redirect stub to /#calculator: make it a real page (calculator explanation, how it estimates, limits, FAQ) or keep as redirect. Rentals follow-up: a static crawlable list of real listings once the Hostflow feed is reachable from the build (hostflow.in blocked from the cloud session on Nov 17). Bing also flags the old URLs /es/rentals and /tours-transportation; check they redirect properly. Add 200–400 words of useful, answer-first copy around the Hostflow embed and the calculator: what's listed, neighborhoods, how booking works, how the calculator estimates and its limits. Add an FAQ block. Don't touch the embeds.

## Done
- 2026-11-17: Rentals page EN `/rentals/` + ES `/es/arriendos/` (item 10, rentals part; items 6 and 7 checked first: 6 duplicates Sol's live 'how to choose' post, 7 mostly done): keyword title/H1/meta ('Furnished apartments for rent in Medellín' / 'Apartamentos amoblados en arriendo en Medellín'), answer-first lead, ~650 words around the untouched Hostflow embed (how booking direct works, short vs monthly stays with RNT/SIRE as of Nov 2026, 4 areas with cited facts, renter checklist), 6-question FAQ + FAQPage schema; old `/es/rentals` now redirects to `/es/arriendos/`; FAQ schema text no longer has a space before punctuation after links (office report mc-2026-11-17-build).
- 2026-11-16: Spanish money pages + internal links (item 1 site part, office report mc-2026-11-16): ES Airbnb page H2 'Su administrador de Airbnb en Medellín' + lead names us 'administrador de Airbnb en Medellín'; EN Airbnb H2 'Full-service short-term rental management in Medellín, Colombia' + areas sentence; home owner section (EN + ES) links exact anchors 'long-term property management in Medellín' / 'administración de rentas largas en Medellín' and 'property management in El Poblado' + Laureles/Envigado/Sabaneta; /faq/ + /team/ leads (EN + ES) link home, Airbnb, long-term and fees pages; ES FAQ title 'Administración de propiedades: preguntas frecuentes'. Item 0 still blocked: es.wikipedia.org, medellin.gov.co, metrodemedellin.gov.co not in the cloud session's allowed network domains (James: allow them in the environment's network settings).
- 2026-11-16: Foreign-owner depth page EN `/property-management-colombia/` + ES `/es/administracion-de-propiedades-colombia/` (items 2, 3 and 4 closed: every landing page now has an answer-first lead and FAQ): bold answer-first lead with 12%/17% + IVA; new sections "Can foreigners own and rent out property in Colombia?" (Constitution Art. 100, ProColombia, cited), Airbnb vs long-term, where we manage (links to all 4 area pages), 8-point vetting checklist (RUES, RNT, matrícula de arrendador); DIAN-cited tax note; 6-question FAQ + FAQPage schema; ~1,570 EN / ~1,715 ES words. Payout method abroad still waits on James (Needs James).
- 2026-11-15: Home EN `/` + ES `/es/` (office report mc-2026-11-15-build, picked while item 0 is blocked on unreachable sources): EN title/meta/og add "Colombia" for the head term; answer-first EN hero lead (who, where, 12%/17% + IVA, no upfront fees, payouts in 5 business days) linking `/airbnb-management-medellin/` (ES lead now links the ES Airbnb page too); keyword H2 "Airbnb and long-term property management"; new FAQ "Do you manage Airbnb apartments in Medellín?" (EN + ES, in FAQPage schema); `priceRange` + `knowsAbout` in the business schema.
- 2026-11-15: Sabaneta area page live, EN `/property-management-sabaneta/` + ES `/es/administracion-de-propiedades-sabaneta/`: answer-first intro (17%/12% + IVA), Airbnb / long-stay / why-us blocks with cited facts (Blu Radio: smallest municipality in Colombia by area; Wikipedia + Metro de Medellín: Sabaneta station on Line A), 6-question FAQ incl. "Is Sabaneta part of Medellín?" + FAQPage schema; now indexable and in sitemap (item 5 closed too). All 4 area pages now live.
- 2026-11-14: Envigado area page live, EN `/property-management-envigado/` + ES `/es/administracion-de-propiedades-envigado/`: answer-first intro (17%/12% + IVA), Airbnb / long-stay / why-us blocks with cited facts (La FM: separate municipality in the Valle de Aburrá; Metro de Medellín Line A: Ayurá and Envigado stations), 6-question FAQ incl. "Is Envigado part of Medellín?" + FAQPage schema. Also fixed sitemap `<lastmod>` for pages that go live (build used the placeholder's old git date): Laureles + Envigado now 2026-11-14.
- 2026-11-14: Laureles area page live, EN `/property-management-laureles/` + ES `/es/administracion-de-propiedades-laureles/`: answer-first intro (17%/12% + IVA), Airbnb / long-stay / why-us blocks with cited local facts (Medellin Guru, Metro de Medellín Line B) and links to Airbnb, long-term, fees, foreign-owner, El Poblado and the month-stay guide; 6-question FAQ + FAQPage schema; now indexable, in sitemap and home/footer area links.
- 2026-11-13: Home pages EN `/` + ES `/es/`: ES title/meta/hero lead lead with "administración de propiedades Medellín" (who, where, 12% + IVA, RNT/SIRE/TRA, payout timing); new "from start to finish" owner section (reglamento + RNT as of Nov 2026, operations, payouts/GAAP, fees with IVA on the commission) linking 4 money pages; 6-question FAQ + FAQPage schema on both (build adds it from the visible FAQ). Picked ahead of item 0 per James's Nov 12 inbox request.
- 2026-11-13: El Poblado area page live, EN `/property-management-el-poblado/` + ES `/es/administracion-de-propiedades-el-poblado/`: answer-first intro (17%/12% + IVA, office in El Poblado), Airbnb / long-stay / why-us blocks with links to Airbnb, long-term, fees and foreign-owner pages, 6-question FAQ + FAQPage schema; now indexable, in sitemap and linked from home Areas cards/footer.
- 2026-11-12: Long-term page live, EN `/long-term-property-management-medellin/` + ES `/es/administracion-de-rentas-largas-medellin/` (ES title targets "arriendos amoblados"): answer-first 12%/15% + IVA intro, short vs long comparison table, payouts/Premium/RNT (as of Nov 2026), how to start, 5-question FAQ + FAQPage schema; now in sitemap and footer links site-wide.
- 2026-11-12: Google rating shown as text ("★ 4.7 on Google · 63 reviews", linked to the Maps profile) in the EN/ES home hero and under the answer-first intro of every live landing page (Airbnb, Colombia) and the fees page; key fact in `llms.txt`. Numbers in `site_config.BUSINESS` (`google_rating`, `google_reviews`, `rating_checked`); no rating schema. Long-term page not live yet (see item 0).
- 2026-11-11: `llms.txt` added, generated each build (commit b4f22a9).
- 2026-11-11: Search Console re-verified under contact@ with the HTML file `googlee590b9a9202680db.html`. Never remove it.
- 2026-11-12: Fees page shipped, EN `/property-management-fees-medellin/` + ES `/es/tarifas-administracion-de-propiedades-medellin/` (answer-first, plan tables, COP example with IVA, fee-model guide, FAQPage schema); linked from home plans note (EN/ES) and FAQ fees answer.
- 2026-11-12: Airbnb management page EN `/airbnb-management-medellin/` + ES `/es/administracion-de-airbnb-medellin/`: answer-first intro with 17%/20% + IVA, 5 new sections (owner checklist incl. RNT/reglamento, fees, payouts/reports, neighborhoods, how to start), 6-question FAQ + FAQPage schema; linked from home plans note (EN/ES) and every blog post that mentions Airbnb (build adds a "Related" link).

## Needs James
- Fees page: is our commission calculated on rental income before or after the platform's (Airbnb/Booking) service fee, and is the guest cleaning fee part of that base? Once confirmed, add one sentence to `_build/fees.py` (EN + ES); it is a top question owners ask.
- Payout currency: do owners abroad get paid in COP, USD, or their choice, and by what method (bank transfer, Wise, etc.)? The Airbnb and foreign-owner pages can't answer "how are payouts sent abroad" until this is confirmed.
- Long-term page: do you also manage unfurnished 12-month leases (Ley 820 de 2003 contracts), and how are long-stay guests or tenants screened? Both are common owner questions; once confirmed, add a sentence and FAQ to the long-term page in `_build/landing.py` (EN + ES).
- Old Wix URL `/property-management/` still redirects to the home page; the comment in `build.py` planned to point it at the long-term page once live. Left on the home page (closer match for a general 'property management' URL) unless you prefer otherwise.
- Rentals page: do monthly guests need a deposit or a Colombian guarantor (fiador), and is booking direct priced differently from Airbnb? Top renter questions; once confirmed, add them to the `/rentals/` FAQ in `_build/build.py` (R dict, EN + ES).
