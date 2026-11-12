# Fees page (/property-management-fees-medellin/, /es/tarifas-administracion-de-propiedades-medellin/).
# Answer-first page for "how much does property management / Airbnb management cost in Medellín".
# Only facts already on the site (plans section, FAQ) plus one cited source (IVA general rate).
# Fees must match the plans section of index.html exactly. Built by build.py, section 4h.

IVA_SOURCE = 'https://actualicese.com/estatutotributario/468-2/'

FEES = {
 'en': dict(
  slug='property-management-fees-medellin', home='Home', crumb='Fees',
  title='Property Management Fees in Medellín (2026)',
  desc='What property management costs in Medellín: 12% + IVA for long stays and 17% + IVA for short stays on Basic, 15% and 20% on Premium. No upfront fees.',
  h1='Property management fees in Medellín (2026): what owners pay',
  lead='<p>Medellín Concierge charges a commission on your rental income, plus IVA, with no upfront fees. On the <strong>Basic</strong> plan it is <strong>12% for long stays</strong> (30+ nights) and <strong>17% for short stays</strong> (Airbnb). On the <strong>Premium</strong> plan it is <strong>15% and 20%</strong>, and we also pay your property taxes, HOA fees, utilities and internet and send you a monthly accounting report.</p>',
  sections=[
   ('Our fees at a glance', '''<table>
        <thead><tr><th></th><th>Long stays (30+ nights)</th><th>Short stays</th></tr></thead>
        <tbody>
          <tr><th>Basic</th><td>12% + IVA</td><td>17% + IVA</td></tr>
          <tr><th>Premium</th><td>15% + IVA</td><td>20% + IVA</td></tr>
        </tbody>
      </table>
      <p>The percentages are commissions on rental income. They do not include IVA (Colombian VAT), which is added to the commission. There is no setup fee and nothing to pay up front: we earn only when your property earns.</p>'''),
   ('What each plan includes', '''<table>
        <thead><tr><th></th><th>Basic</th><th>Premium</th></tr></thead>
        <tbody>
          <tr><th>Listing on Airbnb, Booking.com, Expedia and VRBO, with dynamic pricing and synced calendars</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>24/7 guest support, check-ins and check-outs</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>Cleaning and maintenance, coordinated and supervised</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>RNT, SIRE and TRA registrations and reporting</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>Emergency support</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>Monthly payout within the first 5 business days, with GAAP statements in your owner portal</th><td>Yes</td><td>Yes</td></tr>
          <tr><th>We pay your property taxes, HOA fees, utilities and internet</th><td>No</td><td>Yes</td></tr>
          <tr><th>Monthly accounting report</th><td>No</td><td>Yes</td></tr>
        </tbody>
      </table>
      <p>Prefer to keep cleaning and maintenance yourself? Ask about channel management only: we give live support across the listing channels and handle guest inquiries while you keep control of cleaning and maintenance.</p>'''),
   ('Example: what the commission looks like in pesos', f'''<p>Say a short-stay apartment on the Basic plan earns COP 10,000,000 in rental income in a month. The commission is 17% of that, COP 1,700,000. IVA is then added to the commission: at Colombia’s general IVA rate of 19% (<a href="{IVA_SOURCE}" target="_blank" rel="noopener">Estatuto Tributario, art. 468</a>, as of November 2026), that is COP 323,000, for a total of COP 2,023,000. The same month on a long stay would be 12%, COP 1,200,000 plus IVA.</p>
      <p>This is an illustration of how the percentage works, not an income estimate. For a first idea of what your property could earn, try our <a href="../#calculator">revenue calculator</a>. Tax rules can change: confirm how IVA and income tax apply to you with a qualified accountant.</p>'''),
   ('How property management fees work in Medellín', '''<p>Most managers charge in one of two ways, and some combine them:</p>
      <ul>
        <li><strong>A percentage of rental income.</strong> The manager earns more when you earn more and less in a slow month, so their incentive matches yours. Short stays usually cost a higher percentage than long stays because there are more check-ins, cleanings and guest messages to handle. This is how we charge.</li>
        <li><strong>A fixed monthly fee.</strong> Easier to predict, but you pay the same in a month with few bookings, and the manager earns nothing extra for filling your calendar.</li>
        <li><strong>A base fee plus a smaller percentage.</strong> A mix of the two.</li>
      </ul>
      <p>A low headline percentage is not always the cheapest option. Compare what you would actually pay in a typical month, including everything below.</p>'''),
   ('Extra charges to ask any manager about', '''<ul>
        <li><strong>IVA:</strong> is the quoted percentage before or after IVA? Ours is before: IVA is added.</li>
        <li><strong>Setup or onboarding fees:</strong> some managers charge to create the listing or prepare the apartment. We charge no upfront fees.</li>
        <li><strong>Cleaning:</strong> is the cleaning fee passed through at cost, or does it carry a markup?</li>
        <li><strong>Maintenance and repairs:</strong> is there a markup on contractors, and who approves the cost? With us, repairs above a limit you agree in advance need your approval first.</li>
        <li><strong>Supplies and deep cleaning:</strong> who pays for toiletries, linens and deep cleans? With us, any additional cost like these is discussed with you in advance.</li>
        <li><strong>Registrations:</strong> are RNT, SIRE and TRA included? In both our plans, they are.</li>
        <li><strong>Payouts and reporting:</strong> how often are you paid and what statements do you get? We pay the previous month’s earnings within the first 5 business days, calculated using GAAP, net of our fees and expenses.</li>
        <li><strong>Leaving:</strong> what notice is needed to end the contract, and is there a penalty? You can pause or end our services with advance notice as set out in our agreement, and we hand over smoothly.</li>
      </ul>
      <p>Get the answers in writing before you sign. Our <a href="../faq/">FAQ</a> answers these for us in detail.</p>'''),
  ],
  faq_h='Fees: frequently asked questions',
  faq=[
   ('How much does Airbnb management cost in Medellín?',
    'With Medellín Concierge, Airbnb (short-stay) management costs 17% of rental income plus IVA on the Basic plan, or 20% plus IVA on the Premium plan, which also pays your property taxes, HOA fees, utilities and internet. There are no upfront fees.'),
   ('How much does long-term property management cost?',
    'For stays of 30 nights or more, our commission is 12% of rental income plus IVA on the Basic plan, or 15% plus IVA on Premium.'),
   ('Is IVA included in your percentages?',
    'No. Our percentages do not include IVA (Colombian VAT). IVA is added to our commission.'),
   ('Are there setup fees or hidden fees?',
    'No. There are no upfront fees, and we operate transparently: any additional cost, such as deep cleaning, minor repairs or restocking supplies, is discussed with you in advance.'),
   ('What is the difference between Basic and Premium?',
    'Both include listing on Airbnb, Booking.com, Expedia and VRBO with dynamic pricing, full guest support, cleaning and maintenance, legal compliance management and emergency support. Premium is completely hands-off: we also pay your property taxes, HOA fees, utilities and internet and send a monthly accounting report.'),
   ('When and how do I get paid?',
    'Once a month, within the first 5 business days, for the previous month. Earnings are calculated using GAAP, net of our management fees and expenses, and you can see everything in your owner portal.'),
  ],
  cta_h='Get a proposal for your property', cta_p='Free consultation: we look at your property, estimate its income and recommend a plan.',
  more_h='More for owners',
  more=[('../airbnb-management-medellin/', 'Airbnb management in Medellín'),
        ('../property-management-colombia/', 'Property management in Colombia for foreign owners'),
        ('../faq/', 'Property management FAQ'),
        ('../#plans', 'Compare the plans on our home page')],
 ),
 'es': dict(
  slug='tarifas-administracion-de-propiedades-medellin', home='Inicio', crumb='Tarifas',
  title='Cuánto cobra una administradora en Medellín (2026)',
  desc='Cuánto cuesta la administración de propiedades en Medellín: 12% + IVA en rentas largas y 17% + IVA en Airbnb con el plan Básico. Sin costos iniciales.',
  h1='Cuánto cobra una administradora de propiedades en Medellín (2026)',
  lead='<p>En Medellín Concierge cobramos una comisión sobre los ingresos por renta, más IVA, sin costos iniciales. Con el plan <strong>Básico</strong> es el <strong>12% en estancias largas</strong> (30 noches o más) y el <strong>17% en estancias cortas</strong> (Airbnb). Con el plan <strong>Premium</strong> es el <strong>15% y el 20%</strong>, y además le pagamos el predial, la administración, los servicios públicos e internet, con un reporte contable mensual.</p>',
  sections=[
   ('Nuestras tarifas en resumen', '''<table>
        <thead><tr><th></th><th>Estancias largas (30+ noches)</th><th>Estancias cortas</th></tr></thead>
        <tbody>
          <tr><th>Básico</th><td>12% + IVA</td><td>17% + IVA</td></tr>
          <tr><th>Premium</th><td>15% + IVA</td><td>20% + IVA</td></tr>
        </tbody>
      </table>
      <p>Los porcentajes son comisiones sobre los ingresos por renta y no incluyen el IVA, que se suma a la comisión. No hay cobro de vinculación ni pagos por adelantado: solo ganamos cuando su inmueble genera ingresos.</p>'''),
   ('Qué incluye cada plan', '''<table>
        <thead><tr><th></th><th>Básico</th><th>Premium</th></tr></thead>
        <tbody>
          <tr><th>Publicación en Airbnb, Booking.com, Expedia y VRBO, con precios dinámicos y calendarios sincronizados</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Atención al huésped 24/7, llegadas y salidas</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Limpieza y mantenimiento, coordinados y supervisados</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Registros y reportes de RNT, SIRE y TRA</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Soporte de emergencias</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Pago mensual en los primeros 5 días hábiles, con estados bajo GAAP en su portal de propietario</th><td>Sí</td><td>Sí</td></tr>
          <tr><th>Pagamos su predial, cuota de administración, servicios públicos e internet</th><td>No</td><td>Sí</td></tr>
          <tr><th>Reporte contable mensual</th><td>No</td><td>Sí</td></tr>
        </tbody>
      </table>
      <p>¿Prefiere encargarse usted de la limpieza y el mantenimiento? Pregunte por la gestión de canales: damos soporte en vivo en los canales de publicación y atendemos a los huéspedes, mientras usted maneja el aseo y el mantenimiento.</p>'''),
   ('Ejemplo: cuánto es la comisión en pesos', f'''<p>Suponga que un apartamento de renta corta en el plan Básico genera $10.000.000 de ingresos por renta en un mes. La comisión es el 17%: $1.700.000. A esa comisión se le suma el IVA: con la tarifa general del 19% (<a href="{IVA_SOURCE}" target="_blank" rel="noopener">Estatuto Tributario, art. 468</a>, a noviembre de 2026), son $323.000, para un total de $2.023.000. Ese mismo mes en estancia larga sería el 12%: $1.200.000 más IVA.</p>
      <p>Es un ejemplo de cómo funciona el porcentaje, no una proyección de ingresos. Para una primera idea de lo que podría ganar su inmueble, use nuestra <a href="../#calculator">calculadora de ingresos</a>. Las normas tributarias cambian: confirme con un contador calificado cómo le aplican el IVA y el impuesto de renta.</p>'''),
   ('Cómo cobran las administradoras en Medellín', '''<p>La mayoría cobra de una de estas dos formas, y algunas las combinan:</p>
      <ul>
        <li><strong>Un porcentaje de los ingresos por renta.</strong> La administradora gana más cuando usted gana más y menos en un mes flojo, así que sus intereses van alineados con los suyos. La renta corta suele tener un porcentaje mayor que la larga porque implica más llegadas, más aseos y más mensajes con huéspedes. Así cobramos nosotros.</li>
        <li><strong>Una cuota fija mensual.</strong> Es más fácil de prever, pero usted paga lo mismo aunque el mes tenga pocas reservas, y la administradora no gana nada extra por llenar su calendario.</li>
        <li><strong>Una cuota base más un porcentaje menor.</strong> Una mezcla de las dos.</li>
      </ul>
      <p>El porcentaje más bajo no siempre sale más barato. Compare lo que pagaría de verdad en un mes normal, con todo lo que aparece abajo.</p>'''),
   ('Cobros adicionales que debe preguntarle a cualquier administradora', '''<ul>
        <li><strong>IVA:</strong> ¿el porcentaje que le cotizan es antes o después de IVA? El nuestro es antes: el IVA se suma.</li>
        <li><strong>Vinculación o puesta en marcha:</strong> algunas cobran por crear el anuncio o preparar el apartamento. Nosotros no cobramos nada por adelantado.</li>
        <li><strong>Aseo:</strong> ¿la tarifa de limpieza se traslada al costo o lleva un recargo?</li>
        <li><strong>Mantenimiento y reparaciones:</strong> ¿hay recargo sobre los proveedores y quién aprueba el gasto? Con nosotros, las reparaciones que superen un límite acordado con usted las aprueba usted primero.</li>
        <li><strong>Insumos y aseo profundo:</strong> ¿quién paga los artículos de aseo, la lencería y las limpiezas profundas? Con nosotros, cualquier costo adicional de este tipo se le consulta con anticipación.</li>
        <li><strong>Registros:</strong> ¿están incluidos el RNT, el SIRE y la TRA? En nuestros dos planes, sí.</li>
        <li><strong>Pagos e informes:</strong> ¿cada cuánto le pagan y qué estados de cuenta recibe? Le pagamos lo del mes anterior en los primeros 5 días hábiles, calculado bajo GAAP, descontando nuestras comisiones y los gastos.</li>
        <li><strong>Terminación:</strong> ¿con cuánto aviso puede terminar el contrato y hay penalidad? Puede pausar o terminar nuestros servicios con aviso previo, según el contrato, y le hacemos una entrega ordenada.</li>
      </ul>
      <p>Pida las respuestas por escrito antes de firmar. En nuestras <a href="../preguntas-frecuentes/">preguntas frecuentes</a> las respondemos en detalle.</p>'''),
  ],
  faq_h='Tarifas: preguntas frecuentes',
  faq=[
   ('¿Cuánto cobra una administradora de Airbnb en Medellín?',
    'En Medellín Concierge, la administración de Airbnb (renta corta) cuesta el 17% de los ingresos por renta más IVA en el plan Básico, o el 20% más IVA en el plan Premium, que además paga su predial, administración, servicios públicos e internet. No hay costos iniciales.'),
   ('¿Cuánto cuesta la administración de un arriendo a largo plazo?',
    'Para estancias de 30 noches o más, nuestra comisión es el 12% de los ingresos por renta más IVA en el plan Básico, o el 15% más IVA en Premium.'),
   ('¿Sus porcentajes incluyen IVA?',
    'No. Nuestros porcentajes no incluyen IVA. El IVA se suma a nuestra comisión.'),
   ('¿Hay cobros de vinculación o cargos ocultos?',
    'No. No hay costos iniciales y trabajamos con transparencia: cualquier costo adicional, como una limpieza profunda, reparaciones menores o reposición de insumos, se le consulta con anticipación.'),
   ('¿Qué diferencia hay entre el plan Básico y el Premium?',
    'Los dos incluyen publicación en Airbnb, Booking.com, Expedia y VRBO con precios dinámicos, atención completa al huésped, limpieza y mantenimiento, gestión del cumplimiento legal y soporte de emergencias. Premium es totalmente sin preocupaciones: además pagamos su predial, administración, servicios públicos e internet y le enviamos un reporte contable mensual.'),
   ('¿Cuándo y cómo recibo mis pagos?',
    'Una vez al mes, dentro de los primeros 5 días hábiles, por el mes anterior. Las ganancias se calculan bajo GAAP, descontando nuestras comisiones y los gastos, y usted ve todo en su portal de propietario.'),
  ],
  cta_h='Reciba una propuesta para su inmueble', cta_p='Consulta gratuita: revisamos su inmueble, estimamos sus ingresos y le recomendamos un plan.',
  more_h='Más para propietarios',
  more=[('../administracion-de-airbnb-medellin/', 'Administración de Airbnb en Medellín'),
        ('../administracion-de-propiedades-colombia/', 'Administración de propiedades en Colombia para propietarios extranjeros'),
        ('../preguntas-frecuentes/', 'Preguntas frecuentes'),
        ('../#plans', 'Comparar los planes en la página de inicio')],
 ),
}
