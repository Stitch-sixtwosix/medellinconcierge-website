# SEO landing pages. One entry per page; each has an English and a Spanish version.
#
# FOR LUPA (copy writer): fill in every value marked None with the final text (plain text,
# or simple HTML such as <p>, <ul>, <strong>). While ANY copy value on a page is still None,
# that page shows a dashed "copy coming" box in its place, is marked noindex, and is left
# out of sitemap.xml, so a half-finished page never reaches Google.
#
# Facts that are already verified (plans, payouts, compliance) are rendered by the template
# itself and do not need to be written here.

AREAS = ['el-poblado', 'laureles', 'envigado', 'sabaneta']

PAGES = [
 dict(key='el-poblado', area='El Poblado',
  en=dict(slug='property-management-el-poblado',
          title='Property Management in El Poblado | Medellín Concierge',
          description=None,   # 120–155 characters
          h1='Property management in El Poblado',
          intro=None,
          blocks=[('Airbnb management in El Poblado', None),
                  ('Long-term rental management in El Poblado', None),
                  ('Why El Poblado owners work with us', None)]),
  es=dict(slug='administracion-de-propiedades-el-poblado',
          title='Administración de propiedades en El Poblado, Medellín',
          description=None,
          h1='Administración de propiedades en El Poblado',
          intro=None,
          blocks=[('Administración de Airbnb en El Poblado', None),
                  ('Administración de rentas largas en El Poblado', None),
                  ('Por qué los propietarios de El Poblado trabajan con nosotros', None)])),

 dict(key='laureles', area='Laureles',
  en=dict(slug='property-management-laureles',
          title='Property Management in Laureles | Medellín Concierge',
          description=None, h1='Property management in Laureles', intro=None,
          blocks=[('Airbnb management in Laureles', None),
                  ('Long-term rental management in Laureles', None),
                  ('Why Laureles owners work with us', None)]),
  es=dict(slug='administracion-de-propiedades-laureles',
          title='Administración de propiedades en Laureles, Medellín',
          description=None, h1='Administración de propiedades en Laureles', intro=None,
          blocks=[('Administración de Airbnb en Laureles', None),
                  ('Administración de rentas largas en Laureles', None),
                  ('Por qué los propietarios de Laureles trabajan con nosotros', None)])),

 dict(key='envigado', area='Envigado',
  en=dict(slug='property-management-envigado',
          title='Property Management in Envigado | Medellín Concierge',
          description=None, h1='Property management in Envigado', intro=None,
          blocks=[('Airbnb management in Envigado', None),
                  ('Long-term rental management in Envigado', None),
                  ('Why Envigado owners work with us', None)]),
  es=dict(slug='administracion-de-propiedades-envigado',
          title='Administración de propiedades en Envigado',
          description=None, h1='Administración de propiedades en Envigado', intro=None,
          blocks=[('Administración de Airbnb en Envigado', None),
                  ('Administración de rentas largas en Envigado', None),
                  ('Por qué los propietarios de Envigado trabajan con nosotros', None)])),

 dict(key='sabaneta', area='Sabaneta',
  en=dict(slug='property-management-sabaneta',
          title='Property Management in Sabaneta | Medellín Concierge',
          description=None, h1='Property management in Sabaneta', intro=None,
          blocks=[('Airbnb management in Sabaneta', None),
                  ('Long-term rental management in Sabaneta', None),
                  ('Why Sabaneta owners work with us', None)]),
  es=dict(slug='administracion-de-propiedades-sabaneta',
          title='Administración de propiedades en Sabaneta',
          description=None, h1='Administración de propiedades en Sabaneta', intro=None,
          blocks=[('Administración de Airbnb en Sabaneta', None),
                  ('Administración de rentas largas en Sabaneta', None),
                  ('Por qué los propietarios de Sabaneta trabajan con nosotros', None)])),

 dict(key='colombia', area='Colombia',
  en=dict(slug='property-management-colombia',
          title='Property Management in Colombia for Foreign Owners',
          description=None, h1='Property management in Colombia for foreign owners', intro=None,
          blocks=[('Managing your Colombian property from abroad', None),
                  ('Taxes, registrations and compliance for foreign owners', None),
                  ('Getting paid in your home country', None)]),
  es=dict(slug='administracion-de-propiedades-colombia',
          title='Administración de propiedades en Colombia para extranjeros',
          description=None, h1='Administración de propiedades en Colombia para propietarios extranjeros', intro=None,
          blocks=[('Cómo administrar su propiedad en Colombia desde el exterior', None),
                  ('Impuestos, registros y cumplimiento para propietarios extranjeros', None),
                  ('Cómo recibir sus pagos en su país', None)])),
]
