# Diamond Card venues (/diamond-card/, /es/tarjeta-diamante/): the page the "Membership benefits" button on the
# Wallet pass opens. In page order. noindex and not in the sitemap; reached from the card.
#
# "deal": ONLY what James has confirmed with the venue. None shows "Deal coming soon".
# 2026-11-12: James confirmed a discount at every venue except Medellín Soundbar (welcome cocktail);
# 2026-11-14: James corrected it to 15% off (it was listed as 10%).
# 2026-11-17: James added Glu Glu, TEST Kitchen Lab and Krudo (all at Wake, Cl. 10B #35-27) at 20% off; about lines from
#   their Instagram names, medellin.co's Wake guide and Azure Road; Maps listings link to their Instagram.
# "about": from the venue's own website (Sinmente brands), Hotel Selvario36's page (Ensō) or Instagram bio (Soundbar).
# Each venue's first link opens its Google Maps business listing by place id (cid), each checked 2026-11-12 to be the right
# business (listing links to the venue's own site or booking page, or matches its address).
# sinmente=True: a Sinmente brand (listed on sinmente.co; Ensō confirmed by James 2026-11-17). Guests also need the free Sinmente card for the deal, from
#   SINMENTE_SIGNUP (Sinmente's "Medellín Concierge 15% off" sign-up on Comeback; each guest gets their own card).
# "logo": file in assets/partners/ (same charcoal logos as the home page partners banner).
SINMENTE_SIGNUP = 'https://signup.comeback.es/8324acf9'

VENUES = [
    dict(name='Medellín Soundbar', logo='medellin-soundbar.webp', h=48,
         about=dict(en='Music, cocktails and hookah, with local DJs every night.',
                    es='Música, coctelería y hookah, con DJs locales todas las noches.'),
         deal=dict(en='Welcome cocktail', es='Cóctel de bienvenida'),
         links=[('map', 'https://maps.google.com/?cid=5793242521881675261'), ('instagram', 'https://www.instagram.com/medellin.soundbar/')]),
    dict(name='Mal de Ojo', sinmente=True, logo='mal-de-ojo.webp', h=36,
         about=dict(en='Rooftop in Astorga, El Poblado: panoramic views, fusion cuisine and signature cocktails.',
                    es='Rooftop en Astorga, El Poblado: vista panorámica, cocina de fusión y coctelería de autor.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=11680708231227522908'), ('web', 'https://maldeojo.co/'), ('book', 'https://mal-de-ojo.cluvi.co/bookings/18574')]),
    dict(name='Envy Rooftop', sinmente=True, logo='envy-rooftop.webp', h=32,
         about=dict(en='360° views from the top of The Charlee hotel: signature cocktails, Nikkei sushi and live music.',
                    es='Vista 360° desde lo alto del hotel The Charlee: coctelería de autor, sushi nikkei y música en vivo.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=15876383819380324519'), ('web', 'https://envyrooftop.com/'), ('book', 'https://envy.cluvi.co/')]),
    dict(name='Ensō Rooftop', sinmente=True, logo='enso-rooftop.webp', h=28,
         about=dict(en='Rooftop of Hotel Selvario36 in El Poblado, with views over the Aburrá Valley.',
                    es='Rooftop del Hotel Selvario36 en El Poblado, con vista al valle de Aburrá.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=10876860726802301616'), ('web', 'https://selvario36hotel.com/en/enso-medellin-el-rooftop/'), ('instagram', 'https://www.instagram.com/enso.mde/')]),
    dict(name='Mala Audio Bar', sinmente=True, logo='mala-audio-bar.webp', h=26,
         about=dict(en='A bar where sound comes first: vinyl, high-fidelity audio and signature cocktails in El Poblado.',
                    es='Un bar donde el sonido manda: vinilo, alta fidelidad y coctelería de autor en El Poblado.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=5812808767051517079'), ('web', 'https://malaaudiobar.co/'), ('book', 'https://mala-audio-bar.cluvi.co/bookings/18573')]),
    dict(name='Oni Nikkei', sinmente=True, logo='oni-nikkei.webp', h=34,
         about=dict(en='Sushi where Japan meets Peru: signature cuts, ceviches and cocktails in El Poblado.',
                    es='Sushi donde Japón se encuentra con Perú: cortes de autor, ceviches y coctelería en El Poblado.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=39364356834499871'), ('web', 'https://oninikkei.co/'), ('book', 'https://oni.cluvi.co/bookings/18568')]),
    dict(name='Egeo', sinmente=True, logo='egeo.webp', h=28,
         about=dict(en='Mediterranean cooking to share, with Greek flavors, at the Click Clack hotel in El Poblado.',
                    es='Cocina mediterránea para compartir, con sabores griegos, en el hotel Click Clack de El Poblado.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=7269581412373629980'), ('web', 'https://egeorestaurante.co/'), ('book', 'https://egeo.cluvi.co/bookings/18569')]),
    dict(name='Burdo', sinmente=True, logo='burdo.webp', h=18,
         about=dict(en='American food and drinks on a terrace in Provenza.',
                    es='Comida americana y tragos en una terraza en Provenza.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=11813945638956985323'), ('web', 'https://burdorestaurante.co/'), ('book', 'https://burdo.cluvi.co/bookings/18720')]),
    dict(name='General', sinmente=True, logo='general.webp', h=18,
         about=dict(en='All-day brunch and specialty coffee in El Poblado, with space to work or meet.',
                    es='Brunch todo el día y café de especialidad en El Poblado, con espacio para trabajar o compartir.'),
         deal=dict(en='15% off', es='15% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=4226588920039407470'), ('web', 'https://generalcafe.co/'), ('book', 'https://cafe-general.cluvi.co/bookings/18710')]),
    dict(name='Glu Glu', logo='glu-glu.webp', h=46,
         about=dict(en='Wine bar and wine shop in the Wake complex, El Poblado.',
                    es='Bar de vinos y tienda de vinos en el complejo Wake, El Poblado.'),
         deal=dict(en='20% off', es='20% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=16207558861699760620'), ('instagram', 'https://www.instagram.com/gluglubardevinos/')]),
    dict(name='TEST Kitchen Lab', logo='test-kitchen-lab.webp', h=26,
         about=dict(en='Chef Adolfo Cavalie\'s chef\'s-counter kitchen at Wake, cooking only with Colombian ingredients.',
                    es='La cocina de barra del chef Adolfo Cavalie en Wake, solo con ingredientes colombianos.'),
         deal=dict(en='20% off', es='20% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=510294160514237982'), ('instagram', 'https://www.instagram.com/test.klab/')]),
    dict(name='Krudo Viches & Vinilos', logo='krudo.webp', h=50,
         about=dict(en='Raw bar and seafood with vinyl records, now at Wake in El Poblado.',
                    es='Barra de crudos y mariscos con discos de vinilo, ahora en Wake, El Poblado.'),
         deal=dict(en='20% off', es='20% de descuento'),
         links=[('map', 'https://maps.google.com/?cid=7382530811463103952'), ('instagram', 'https://www.instagram.com/krudovichesyvinilos/')]),
]


DIAMOND = {
    'en': dict(slug='diamond-card', title='Diamond Card: partner bars and restaurants | Medellín Concierge',
               desc='Diamond Card benefits for Medellín Concierge guests: partner bars and restaurants in Medellín and the deal at each one.',
               kicker='Guest benefit', h1='Diamond Card',
               lead='Show your Diamond Card at these bars and restaurants to get each one’s deal. Valid during your stay with Medellín Concierge.',
               deal='Your deal', soon='Deal coming soon',
               sin_kicker='Sinmente venues', sin_h='Get the free Sinmente card too',
               sin_p='At the Sinmente venues (Mal de Ojo, Envy Rooftop, Ensō Rooftop, Mala Audio Bar, Oni Nikkei, Egeo, Burdo and General) the deal also needs the Sinmente card. Sign up once (about 2 minutes), add it to your Wallet, and show it with your Diamond Card.',
               sin_btn='Get the Sinmente card', sin_line='Also show your Sinmente card', own_line='Just show your Diamond Card',
               link=dict(map='Map', web='Website', book='Book', instagram='Instagram'),
               note='Deals are offered by each venue and may change. Questions or help with a reservation?',
               wa='Message us on WhatsApp', wa_text='Hi! I have a question about my Diamond Card.'),
    'es': dict(slug='es/tarjeta-diamante', title='Tarjeta Diamante: bares y restaurantes aliados | Medellín Concierge',
               desc='Beneficios de la Tarjeta Diamante para huéspedes de Medellín Concierge: bares y restaurantes aliados en Medellín y el beneficio en cada uno.',
               kicker='Beneficio para huéspedes', h1='Tarjeta Diamante',
               lead='Muestre su Tarjeta Diamante en estos bares y restaurantes para recibir el beneficio de cada uno. Válida durante su estadía con Medellín Concierge.',
               deal='Su beneficio', soon='Beneficio muy pronto',
               sin_kicker='Lugares Sinmente', sin_h='Obtenga también la tarjeta Sinmente gratis',
               sin_p='En los lugares Sinmente (Mal de Ojo, Envy Rooftop, Ensō Rooftop, Mala Audio Bar, Oni Nikkei, Egeo, Burdo y General) el beneficio también requiere la tarjeta Sinmente. Regístrese una vez (unos 2 minutos), agréguela a su Wallet y muéstrela junto con su Tarjeta Diamante.',
               sin_btn='Obtener la tarjeta Sinmente', sin_line='Muestre también su tarjeta Sinmente', own_line='Solo muestre su Tarjeta Diamante',
               link=dict(map='Mapa', web='Web', book='Reservar', instagram='Instagram'),
               note='Cada lugar ofrece su propio beneficio y puede cambiar. ¿Preguntas o ayuda con una reserva?',
               wa='Escríbanos por WhatsApp', wa_text='¡Hola! Tengo una pregunta sobre mi Tarjeta Diamante.'),
}
