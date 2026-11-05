# Newsletter: website → Hostflow → subscribers

The website collects signups; Hostflow stores subscribers and sends each new blog post by email (via Twilio).

## Website side (done)

- Signup form in the footer of every page (English and Spanish), hidden while `NEWSLETTER_ENDPOINT` in
  `_build/site_config.py` is empty. Set it to Hostflow's URL, run `python3 _build/build.py`, publish.
- Blog feeds with each post's full text (links already absolute, ready to put in an email):
  - English: `https://www.medellinconcierge.net/blog/feed.xml`
  - Spanish: `https://www.medellinconcierge.net/es/blog/feed.xml`
  Each item has `title`, `link`, `guid` (stable, = link), `pubDate`, `description` (summary) and
  `content:encoded` (full HTML body).

## What Hostflow needs (to build in the Hostflow code)

### 1. Signup endpoint

`POST <NEWSLETTER_ENDPOINT>` with `Content-Type: application/json`:

```json
{ "email": "owner@example.com", "consent": true, "lang": "en", "source": "/blog/" }
```

- `lang` is `en` or `es` (the page language); send that subscriber the matching feed.
- `consent` is always `true` (the form requires the checkbox). Store it with a timestamp, the IP and the
  `source` page as proof of consent (Colombia's Ley 1581 de 2012 on personal data).
- Respond `2xx` on success (also when the address is already subscribed). Any other status shows the
  visitor an error asking them to try again or email sales@medellinconcierge.net.
- CORS: allow origin `https://www.medellinconcierge.net` (and `https://medellinconcierge.net`), method
  `POST`, header `Content-Type`; answer the `OPTIONS` preflight.
- Recommended: double opt-in (a confirmation email before the first newsletter), basic rate limiting,
  and ignore obviously fake addresses.

### 2. Sending new posts

- Check both feeds on a schedule (e.g. hourly). A post is new when its `guid` has not been sent before
  to that language's list; remember sent `guid`s so nothing goes out twice.
- On the very first run, mark the existing posts as already sent (otherwise every old post goes out at once).
- Email: subject = post `title`; body = `content:encoded`, with the logo, a "Read on the website" link
  (`link`) and the footer below.
- Every email needs a one-click unsubscribe link (and a `List-Unsubscribe` header) that works without
  logging in, plus the sender's name and postal address:
  Medellín Concierge S.A.S., Cl. 10 #42-28, Oficina 15, El Poblado, Medellín, Antioquia, Colombia.
- Send from an address on medellinconcierge.net. If Twilio SendGrid sends it, add SendGrid's records to the
  domain's DNS (SPF include / DKIM CNAMEs) so emails don't land in spam. The existing MX and HubSpot SPF
  records must stay.

## Turning it on

1. Hostflow endpoint and sending are live and tested with a test address.
2. Put the endpoint URL in `NEWSLETTER_ENDPOINT`, build, check a signup on the preview, publish.
