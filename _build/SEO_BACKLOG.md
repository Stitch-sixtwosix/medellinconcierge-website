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
0. **Unpublished area pages (found Nov 12):** the Laureles, Envigado and Sabaneta pages still have `None` copy slots in `_build/landing.py`, so they redirect to the home page and are not indexed. Write them like the El Poblado page (answer-first intro with fees, 3 blocks, 6-question FAQ; only site facts). Laureles next. (El Poblado shipped Nov 13; long-term page shipped Nov 12.) Follow-up for El Poblado: the office report's local facts (Comuna 14, Metro Línea A Poblado station, Feria de las Flores, Ley 142 estrato 5/6 surcharge) were left out because medellin.gov.co and wikipedia were unreachable from the cloud session on Nov 13; add them with a cited link once a source can be opened.
1. **Spanish money pages:**
   - Strengthen `/es/` (administración de propiedades Medellín). (`/es/administracion-de-airbnb-medellin/` got keyword-first intro, owner sections and FAQ on Nov 12; remaining for it: links from Spanish blog bodies are Sol's lane.)
   - Use the exact keyword in the title, H1 and first sentence.
   - Add 300–500 words of native Spanish copy for owners: RNT, building rules, payouts in pesos or dollars, reports. Only use facts the site already states.
   - Add an FAQ block with FAQPage schema.
   - Add internal links from every Spanish blog post.
2. **Answer-first summaries on every landing page:** 2–3 sentences right under the H1. Who we are, where, what's included, and the price from X% + IVA.
3. **FAQ blocks on every landing page:** 4–6 questions each, with FAQPage schema, matching the questions owners ask AI.
   - Examples: "How much does Airbnb management cost in Medellín?", "Can a foreigner own and rent out property in Medellín?", "Do I need an RNT?", "How are payouts sent abroad?".
   - Answer only from facts on the site.
4. **"Property management for foreign owners" depth page:** make `/property-management-colombia/` and its Spanish version the best answer to "property manager in Medellín for a foreign owner".
   - Cover payouts, reporting, what the owner must do (RNT, building approval), and how to vet a manager, with a checklist.
5. **Finish the Sabaneta area page.** The build currently notes the copy isn't finished, so the page redirects.
   - Write unique, factual local copy in EN and ES. General, verifiable facts only.
6. **Comparison guide:** "How to compare property management companies in Medellín", with a checklist table: fees, payout timing, reporting, licensing, contract length, references.
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

10. **Thin pages flagged by Bing (Nov 12, 2026):** /rentals/ (with /es/arriendos/) and /airbnb-revenue-calculator/ (with /es/airbnb-revenue-calculator/). Bing also flags the old URLs /es/rentals and /tours-transportation; check they redirect properly. Add 200–400 words of useful, answer-first copy around the Hostflow embed and the calculator: what's listed, neighborhoods, how booking works, how the calculator estimates and its limits. Add an FAQ block. Don't touch the embeds.

## Done
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
