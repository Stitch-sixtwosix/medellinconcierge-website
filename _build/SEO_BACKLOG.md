# SEO and AI-search backlog

The **Lupa · ship** cloud routine works through this list on its own. On each run it takes the top `todo` item, ships it to the site, and moves it to Done with the date and commit. Anyone can add items. Highest value goes first.

Goal (James, Nov 11 2026): #1 on Google, and named by AI answers (Google AI Overviews, ChatGPT, Perplexity, Gemini, Copilot), for property management / Airbnb management in Medellín and Colombia, in English and Spanish.

## What we know (Nov 11–12, 2026)
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
1. **Spanish money pages:**
   - Strengthen `/es/administracion-de-airbnb-medellin/` and `/es/` (administración de propiedades Medellín).
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

## Done
- 2026-11-11: `llms.txt` added, generated each build (commit b4f22a9).
- 2026-11-11: Search Console re-verified under contact@ with the HTML file `googlee590b9a9202680db.html`. Never remove it.
- 2026-11-12: Fees page shipped, EN `/property-management-fees-medellin/` + ES `/es/tarifas-administracion-de-propiedades-medellin/` (answer-first, plan tables, COP example with IVA, fee-model guide, FAQPage schema); linked from home plans note (EN/ES) and FAQ fees answer.

## Needs James
- Fees page: is our commission calculated on rental income before or after the platform's (Airbnb/Booking) service fee, and is the guest cleaning fee part of that base? Once confirmed, add one sentence to `_build/fees.py` (EN + ES); it is a top question owners ask.
