# Business facts used in structured data (JSON-LD), the footer and landing pages.
# Only verified facts go here. Anything not yet confirmed by James stays in TODO_SAME_AS
# and is NOT published until it has a real URL.

SITE = 'https://www.medellinconcierge.net/'

BUSINESS = {
    'name': 'Medellín Concierge',
    'legal_name': 'Medellín Concierge S.A.S.',          # as on the 2026 brochure / Hostflow
    'tax_id': '901564260-7',                             # NIT, confirmed by James 2026-11-11
    'telephone': '+57 304 277 3864',
    'email': 'sales@medellinconcierge.net',
    'street': 'Cl. 10 #42-28, Oficina 15, El Poblado',
    'locality': 'Medellín',
    'region': 'Antioquia',
    'country': 'CO',
    'lat': 6.2104748, 'lng': -75.569858,                 # Google Maps pin of the office
    'map': 'https://maps.app.goo.gl/Z1Edu7BPoXGiPpqh8',
    # Google Business Profile rating, as seen by James on the profile (Nov 12, 2026). Shown as text linked to
    # the profile; never as AggregateRating/Review schema (self-serving for a business's own site).
    'google_rating': 4.7, 'google_reviews': 63, 'rating_checked': 'Nov 2026',
    'area_served': ['Medellín', 'El Poblado', 'Laureles', 'Envigado', 'Sabaneta', 'Colombia'],
    'services_en': ['Property management', 'Airbnb management', 'Short-term rental management',
                    'Long-term rental management', 'Channel management', 'Vacation rental management'],
    'services_es': ['Administración de propiedades', 'Administración de Airbnb', 'Administración de rentas cortas',
                    'Administración de rentas largas', 'Gestión de canales', 'Administración de alquileres vacacionales'],
}

# Profiles that exist and are confirmed (published in sameAs)
SAME_AS = [
    'https://www.airbnb.com/users/show/446836447',
    'https://www.instagram.com/medellin.concierge/',      # verified 2026-11-04: "MEDCON | Property Management"
    'https://maps.app.goo.gl/Z1Edu7BPoXGiPpqh8',         # Google Maps listing (also in hasMap)
    'https://www.facebook.com/luxmedellinconcierge',      # verified 2026-11-05: "Medellín Concierge", linked from the old Wix site
    'https://www.linkedin.com/company/medellin-concierge-sas/',   # verified 2026-11-05: "Medellin Concierge, SAS"
]

# PLACEHOLDERS for James: paste the real URL to the right of each, then move it into SAME_AS.
TODO_SAME_AS = {
    'Google Business Profile (full URL, not the maps.app.goo.gl short link)': '',
}

# Newsletter signup (footer of every page). Leave '' to keep the form hidden.
# When set, the form POSTs JSON {email, consent, lang, source} to this URL; see _build/NEWSLETTER.md.
NEWSLETTER_ENDPOINT = ''
INDEXNOW_KEY = '4ba685f5507100f199dd44c2a2c1c263'   # IndexNow key; the file /4ba685f5507100f199dd44c2a2c1c263.txt on the site proves we own it
