# Airbnb revenue calculator page (/airbnb-revenue-calculator/, /es/calculadora-ingresos-airbnb-medellin/).
# Old Wix URL made into a real page (Bing flagged the redirect stub as thin, Nov 12 2026). The calculator itself is
# the same widget as the home page (#calculator section + its inline script), copied by build.py section 4i,
# so the two never drift apart. Only facts already on the site plus one cited source (IVA general rate).
# Fees must match the plans section of index.html exactly.

from fees import IVA_SOURCE

CALC = {
 'en': dict(
  slug='airbnb-revenue-calculator', home='Home', crumb='Revenue calculator',
  title='Airbnb Revenue Calculator for Medellín (2026)',
  desc='Estimate what your Medellín apartment could earn on Airbnb by area, bedrooms, nightly rate and occupancy, and see how fees and IVA change what you keep.',
  h1='Airbnb revenue calculator for Medellín',
  lead='<p>The calculator below estimates an apartment’s <strong>gross Airbnb revenue</strong> in Medellín: your <strong>average nightly rate × the nights booked in an average month</strong> (30.4 days × occupancy). At USD 110 a night and 70% occupancy that is about <strong>USD 2,340 a month</strong>. It is a ballpark before platform fees, management (ours is 17% + IVA for short stays on the Basic plan), cleaning, utilities and taxes; for an estimate of your own property, <a href="../#contact">request a free consultation</a>.</p>',
  after_calc='<p class="fine">Prefer the long-stay route? The same nightly maths does not apply to stays of 30 nights or more, which are priced by the month: see <a href="../long-term-property-management-medellin/">long-term property management in Medellín</a>.</p>',
  sections=[
   ('How the calculator estimates your revenue', '''<p>It uses three numbers and one simple formula:</p>
      <ul>
        <li><strong>Average nightly rate (USD):</strong> what guests pay per night on average across the month, not your peak-date price.</li>
        <li><strong>Occupancy:</strong> the share of nights that are booked. Nights booked per month = 30.4 × occupancy, so 70% is about 21 nights.</li>
        <li><strong>Gross monthly revenue</strong> = nightly rate × nights booked. The yearly figure is simply that month × 12.</li>
      </ul>
      <p>The <strong>neighborhood</strong> and <strong>bedrooms</strong> buttons only set a starting nightly rate for the slider: USD 95 for a one-bedroom in El Poblado, 80 in Laureles, 70 in Envigado, 65 in Sabaneta and 60 elsewhere, plus USD 35 for each extra bedroom. They are a convenient starting point, not market data for your building. Move the rate and occupancy sliders to what comparable listings near you actually achieve, and the result updates instantly.</p>'''),
   ('From gross revenue to what you keep', f'''<p>The big number is <strong>gross</strong> revenue. To see what reaches you, take off the costs of running the apartment. For illustration, if the USD 2,340 from the example were the month’s rental income:</p>
      <table>
        <thead><tr><th></th><th>Basic plan (short stays)</th><th>Premium plan (short stays)</th></tr></thead>
        <tbody>
          <tr><th>Rental income</th><td>USD 2,340</td><td>USD 2,340</td></tr>
          <tr><th>Our commission</th><td>17%: USD 397.80</td><td>20%: USD 468.00</td></tr>
          <tr><th>IVA on the commission (19%)</th><td>USD 75.58</td><td>USD 88.92</td></tr>
          <tr><th>Before other costs</th><td>USD 1,866.62</td><td>USD 1,783.08</td></tr>
          <tr><th>Property tax, HOA fees, utilities and internet</th><td>Paid by you</td><td>Paid by us</td></tr>
        </tbody>
      </table>
      <p>IVA is added to our commission at Colombia’s general rate of 19% (<a href="{IVA_SOURCE}" target="_blank" rel="noopener">Estatuto Tributario, art. 468</a>, as of November 2026). Other costs to budget for: the booking platform’s own fees, cleaning, toiletries and linens, the building’s HOA fee (cuota de administración), property tax (predial), utilities and internet, and income tax on your rental income. There are no upfront fees with us; full details and an example in pesos are on <a href="../property-management-fees-medellin/">our fees page</a>.</p>
      <p>This table shows how the percentages work, not an income forecast. Tax rules can change: confirm how IVA and income tax apply to you with a qualified accountant.</p>'''),
   ('What moves the numbers', '''<ul>
        <li><strong>Nightly rate across the year.</strong> Demand changes with the season, local events and the day of the week. We adjust rates with dynamic pricing so peak dates are not underpriced and quiet weeks still fill.</li>
        <li><strong>Occupancy.</strong> A listing on Airbnb, Booking.com, Expedia and VRBO reaches more guests than one platform alone; we keep all of them on one synced calendar so there are no double bookings.</li>
        <li><strong>Location and building.</strong> Area, view, amenities and how close the apartment is to transport and restaurants all shape what guests will pay. See our pages on <a href="../property-management-el-poblado/">El Poblado</a>, <a href="../property-management-laureles/">Laureles</a>, <a href="../property-management-envigado/">Envigado</a> and <a href="../property-management-sabaneta/">Sabaneta</a>.</li>
        <li><strong>The listing itself.</strong> Photos, description, minimum stays, reviews and fast replies to guests all affect both rate and occupancy.</li>
      </ul>'''),
   ('What this estimate leaves out', '''<ul>
        <li><strong>Seasonality.</strong> The calculator uses one average month. Real months go up and down, and a new listing usually needs time to collect its first reviews.</li>
        <li><strong>Building rules.</strong> Some buildings’ reglamento de propiedad horizontal does not allow short stays. Check it before you count on Airbnb income; if short stays are not allowed, stays of 30 nights or more may be the option.</li>
        <li><strong>Registration.</strong> As of November 2026, an apartment rented to tourists for short stays in Colombia needs a Registro Nacional de Turismo (RNT), and foreign guests are reported to Migración Colombia through SIRE. We manage the RNT, SIRE and TRA for the properties we manage; read <a href="../blog/is-airbnb-legal-in-medellin-rnt-tra-sire.html">is Airbnb legal in Medellín? RNT, TRA and SIRE explained</a>. Rules can change, so confirm your own obligations with a qualified professional.</li>
        <li><strong>Exchange rate.</strong> The calculator works in US dollars for convenience. Your income and costs in Colombia are in pesos, so the dollar figure moves with the exchange rate.</li>
      </ul>'''),
  ],
  faq_h='Revenue calculator: frequently asked questions',
  faq=[
   ('How much can an Airbnb apartment in Medellín earn?',
    'It depends on the nightly rate the apartment can command and how many nights it is booked, which vary with the area, the building, the size and the season. The calculator on this page multiplies the two to give a monthly gross figure; for an estimate of your own property, request a free consultation.'),
   ('How does the revenue calculator work?',
    'Gross monthly revenue = average nightly rate × nights booked, where nights booked = 30.4 × occupancy. The neighborhood and bedroom buttons only set a starting nightly rate; adjust the rate and occupancy sliders to what comparable listings near you achieve.'),
   ('Does the estimate include fees and taxes?',
    'No. It is gross revenue, before platform fees, management fees, cleaning, utilities and taxes. Our commission for short stays is 17% + IVA on the Basic plan or 20% + IVA on Premium, which also pays your property taxes, HOA fees, utilities and internet.'),
   ('What occupancy should I enter?',
    'Use what comparable listings near your apartment achieve over a full year, not just in the busiest months. The slider starts at 70% as an example, not as a forecast for your property.'),
   ('Can you give me an estimate for my specific property?',
    'Yes. In a free consultation we look at your property, estimate its income and recommend a plan, for short stays, long stays of 30 nights or more, or both.'),
   ('How much does Airbnb management cost in Medellín?',
    'With Medellín Concierge, short-stay management costs 17% of rental income plus IVA on the Basic plan, or 20% plus IVA on Premium. Long stays of 30+ nights are 12% or 15% plus IVA. There are no upfront fees.'),
  ],
  cta_h='Get an estimate for your property', cta_p='Free consultation: we look at your property, estimate its income and recommend a plan.',
  more_h='More for owners',
  more=[('../airbnb-management-medellin/', 'Airbnb management in Medellín'),
        ('../property-management-fees-medellin/', 'Property management fees in Medellín'),
        ('../long-term-property-management-medellin/', 'Long-term property management in Medellín'),
        ('../blog/how-much-does-airbnb-management-cost-medellin.html', 'How much Airbnb management costs in Medellín')],
 ),
 'es': dict(
  slug='calculadora-ingresos-airbnb-medellin', home='Inicio', crumb='Calculadora de ingresos',
  title='Calculadora de ingresos Airbnb en Medellín (2026)',
  desc='Calcule cuánto podría generar su apartamento en Airbnb en Medellín según sector, habitaciones, tarifa y ocupación, y cuánto le queda tras comisión e IVA.',
  h1='Calculadora de ingresos de Airbnb en Medellín',
  lead='<p>La calculadora de abajo estima el <strong>ingreso bruto en Airbnb</strong> de un apartamento en Medellín: <strong>tarifa promedio por noche × noches reservadas en un mes promedio</strong> (30,4 días × ocupación). Con USD 110 la noche y 70% de ocupación, da unos <strong>USD 2.340 al mes</strong>. Es una cifra aproximada antes de comisiones de plataforma, administración (la nuestra es 17% + IVA en renta corta con el plan Básico), aseo, servicios e impuestos; para una estimación de su propio inmueble, <a href="../#contact">solicite una consulta gratuita</a>.</p>',
  after_calc='<p class="fine">¿Prefiere la renta larga? Las estancias de 30 noches o más se cobran por mes, no por noche, así que esta cuenta no aplica igual: vea la <a href="../administracion-de-rentas-largas-medellin/">administración de rentas largas en Medellín</a>.</p>',
  sections=[
   ('Cómo calcula sus ingresos', '''<p>Usa tres datos y una fórmula sencilla:</p>
      <ul>
        <li><strong>Tarifa promedio por noche (USD):</strong> lo que pagan los huéspedes en promedio durante el mes, no el precio de las fechas de mayor demanda.</li>
        <li><strong>Ocupación:</strong> el porcentaje de noches reservadas. Noches reservadas al mes = 30,4 × ocupación; con 70% son unas 21 noches.</li>
        <li><strong>Ingreso bruto mensual</strong> = tarifa por noche × noches reservadas. La cifra anual es ese mes × 12.</li>
      </ul>
      <p>Los botones de <strong>barrio</strong> y <strong>habitaciones</strong> solo ponen una tarifa inicial en el control: USD 95 para un apartamento de una habitación en El Poblado, 80 en Laureles, 70 en Envigado, 65 en Sabaneta y 60 en otros sectores, más USD 35 por cada habitación adicional. Son un punto de partida práctico, no datos de mercado de su edificio. Mueva la tarifa y la ocupación a lo que logran anuncios parecidos cerca de usted y el resultado se actualiza al instante.</p>'''),
   ('Del ingreso bruto a lo que le queda', f'''<p>La cifra grande es el ingreso <strong>bruto</strong>. Para ver lo que le llega, hay que descontar lo que cuesta operar el apartamento. A modo de ejemplo, si los USD 2.340 fueran los ingresos por renta del mes:</p>
      <table>
        <thead><tr><th></th><th>Plan Básico (renta corta)</th><th>Plan Premium (renta corta)</th></tr></thead>
        <tbody>
          <tr><th>Ingresos por renta</th><td>USD 2.340</td><td>USD 2.340</td></tr>
          <tr><th>Nuestra comisión</th><td>17%: USD 397,80</td><td>20%: USD 468,00</td></tr>
          <tr><th>IVA sobre la comisión (19%)</th><td>USD 75,58</td><td>USD 88,92</td></tr>
          <tr><th>Antes de otros costos</th><td>USD 1.866,62</td><td>USD 1.783,08</td></tr>
          <tr><th>Predial, cuota de administración, servicios públicos e internet</th><td>Los paga usted</td><td>Los pagamos nosotros</td></tr>
        </tbody>
      </table>
      <p>El IVA se suma a nuestra comisión con la tarifa general del 19% (<a href="{IVA_SOURCE}" target="_blank" rel="noopener">Estatuto Tributario, art. 468</a>, a noviembre de 2026). Otros costos que debe tener en cuenta: las comisiones de la plataforma de reservas, el aseo, los artículos de aseo y la lencería, la cuota de administración del edificio, el predial, los servicios públicos e internet, y el impuesto de renta sobre lo que recibe. Con nosotros no hay costos iniciales; el detalle completo, con un ejemplo en pesos, está en <a href="../tarifas-administracion-de-propiedades-medellin/">nuestras tarifas</a>.</p>
      <p>La tabla muestra cómo funcionan los porcentajes, no es una proyección de ingresos. Las normas tributarias cambian: confirme con un contador calificado cómo le aplican el IVA y el impuesto de renta.</p>'''),
   ('Qué hace subir o bajar la cifra', '''<ul>
        <li><strong>La tarifa a lo largo del año.</strong> La demanda cambia con la temporada, los eventos de la ciudad y el día de la semana. Ajustamos las tarifas con precios dinámicos para no regalar las fechas de alta demanda y llenar también las semanas tranquilas.</li>
        <li><strong>La ocupación.</strong> Un anuncio en Airbnb, Booking.com, Expedia y VRBO llega a más huéspedes que uno en una sola plataforma; manejamos todos en un calendario sincronizado, sin reservas dobles.</li>
        <li><strong>El sector y el edificio.</strong> El barrio, la vista, las zonas comunes y la cercanía al transporte y a los restaurantes influyen en lo que el huésped está dispuesto a pagar. Vea nuestras páginas de <a href="../administracion-de-propiedades-el-poblado/">El Poblado</a>, <a href="../administracion-de-propiedades-laureles/">Laureles</a>, <a href="../administracion-de-propiedades-envigado/">Envigado</a> y <a href="../administracion-de-propiedades-sabaneta/">Sabaneta</a>.</li>
        <li><strong>El anuncio.</strong> Las fotos, la descripción, las estancias mínimas, las reseñas y la rapidez en responder afectan tanto la tarifa como la ocupación.</li>
      </ul>'''),
   ('Lo que esta estimación no incluye', '''<ul>
        <li><strong>La temporada.</strong> La calculadora usa un mes promedio. Los meses reales suben y bajan, y un anuncio nuevo suele necesitar tiempo para reunir sus primeras reseñas.</li>
        <li><strong>El reglamento del edificio.</strong> Algunos reglamentos de propiedad horizontal no permiten la renta corta. Revíselo antes de contar con ingresos de Airbnb; si no se permite, las estancias de 30 noches o más pueden ser la alternativa.</li>
        <li><strong>El registro.</strong> A noviembre de 2026, un apartamento que se arrienda a turistas por noches en Colombia necesita el Registro Nacional de Turismo (RNT), y los huéspedes extranjeros se reportan a Migración Colombia en el SIRE. Nosotros gestionamos el RNT, el SIRE y la TRA de los inmuebles que administramos; lea <a href="../blog/is-airbnb-legal-in-medellin-rnt-tra-sire.html">el Registro Nacional de Turismo para vivienda turística</a>. Las normas pueden cambiar, así que confirme sus obligaciones con un profesional calificado.</li>
        <li><strong>La tasa de cambio.</strong> La calculadora trabaja en dólares por practicidad. Sus ingresos y costos en Colombia son en pesos, así que la cifra en dólares se mueve con la tasa de cambio.</li>
      </ul>'''),
  ],
  faq_h='Calculadora de ingresos: preguntas frecuentes',
  faq=[
   ('¿Cuánto puede ganar un apartamento en Airbnb en Medellín?',
    'Depende de la tarifa por noche que pueda cobrar y de cuántas noches se reserve, y eso cambia con el sector, el edificio, el tamaño y la temporada. La calculadora de esta página multiplica las dos cosas y da un ingreso bruto mensual; para una estimación de su propio inmueble, solicite una consulta gratuita.'),
   ('¿Cómo funciona la calculadora de ingresos?',
    'Ingreso bruto mensual = tarifa promedio por noche × noches reservadas, y noches reservadas = 30,4 × ocupación. Los botones de barrio y habitaciones solo ponen una tarifa inicial; ajuste la tarifa y la ocupación a lo que logran anuncios parecidos cerca de usted.'),
   ('¿La estimación incluye comisiones e impuestos?',
    'No. Es el ingreso bruto, antes de comisiones de plataforma, administración, aseo, servicios e impuestos. Nuestra comisión en renta corta es 17% + IVA en el plan Básico o 20% + IVA en Premium, que además paga su predial, administración, servicios públicos e internet.'),
   ('¿Qué ocupación debo poner?',
    'La que logran anuncios parecidos cerca de su apartamento durante todo el año, no solo en los meses de más demanda. El control arranca en 70% como ejemplo, no como pronóstico para su inmueble.'),
   ('¿Me pueden dar una estimación para mi inmueble?',
    'Sí. En una consulta gratuita revisamos su inmueble, estimamos sus ingresos y le recomendamos un plan, para renta corta, renta larga de 30 noches o más, o ambas.'),
   ('¿Cuánto cobra una administradora de Airbnb en Medellín?',
    'En Medellín Concierge, la renta corta cuesta el 17% de los ingresos por renta más IVA en el plan Básico, o el 20% más IVA en Premium. Las estancias de 30 noches o más cuestan el 12% o el 15% más IVA. No hay costos iniciales.'),
  ],
  cta_h='Reciba una estimación para su inmueble', cta_p='Consulta gratuita: revisamos su inmueble, estimamos sus ingresos y le recomendamos un plan.',
  more_h='Más para propietarios',
  more=[('../administracion-de-airbnb-medellin/', 'Administración de Airbnb en Medellín'),
        ('../tarifas-administracion-de-propiedades-medellin/', 'Tarifas de administración de propiedades en Medellín'),
        ('../administracion-de-rentas-largas-medellin/', 'Administración de rentas largas en Medellín'),
        ('../blog/how-much-does-airbnb-management-cost-medellin.html', 'Cuánto cobra un administrador de Airbnb en Medellín')],
 ),
}
