# Meet the team (/team/, /es/equipo/). In page order.
# "photo" is the file name in assets/team/ (without .webp), made by team_photos.py from team-photos/<photo>.jpg.
# A missing photo shows the person's initials until it is added.
#
# "bio": the person's role and responsibilities, written only from services the site already describes.
# Do not add experience, credentials, degrees or achievements unless James confirms them, and never add
# personal or work email addresses (all contact goes through sales@ and WhatsApp).
TEAM = [
    dict(name='James Duerr', photo='james-duerr',
         role=dict(en='Owner & General Manager', es='Propietario y gerente general'),
         bio=dict(en='James leads Medellín Concierge and its team, overseeing operations, service standards and the relationship with property owners, from short-term apartments to hotels and full buildings.',
                  es='James dirige Medellín Concierge y su equipo. Supervisa la operación, los estándares de servicio y la relación con los propietarios, desde apartamentos de estadía corta hasta hoteles y edificios completos.')),
    dict(name='Angie Pineda', photo='angie-pineda',
         role=dict(en='Operations Manager', es='Gerente de operaciones'),
         bio=dict(en='Angie oversees the success of the company\'s daily operations, creates and maintains our listings on the booking platforms and keeps control of our pricing strategy.',
                  es='Angie supervisa el buen funcionamiento de la operación diaria de la empresa, crea y mantiene nuestros anuncios en las plataformas de reserva y lleva el control de nuestra estrategia de precios.')),
    dict(name='Carlos Alfredo Ruiz', photo='carlos-alfredo-ruiz',
         role=dict(en='Property Manager', es='Administrador de propiedades'),
         bio=dict(en='Carlos handles the day-to-day care of the properties we manage, coordinating and supervising cleaning and maintenance so every home is ready for its next guest.',
                  es='Carlos se encarga del cuidado diario de las propiedades que administramos: coordina y supervisa el aseo y el mantenimiento para que cada propiedad esté lista para el siguiente huésped.')),
    dict(name='Santiago Holguín', photo='santiago-holguin',
         role=dict(en='Property Manager', es='Administrador de propiedades'),
         bio=dict(en='Santiago handles the day-to-day care of the properties we manage, coordinating and supervising cleaning and maintenance so every home is ready for its next guest.',
                  es='Santiago se encarga del cuidado diario de las propiedades que administramos: coordina y supervisa el aseo y el mantenimiento para que cada propiedad esté lista para el siguiente huésped.')),
    dict(name='Carolina Jaramillo', photo='carolina-jaramillo',
         role=dict(en='Guest Manager', es='Gerente de huéspedes'),
         bio=dict(en='Carolina looks after our guests from booking to check-out, answering their messages, coordinating check-ins and resolving questions quickly as part of our 24/7 guest support.',
                  es='Carolina atiende a nuestros huéspedes desde la reserva hasta la salida: responde sus mensajes, coordina los check-ins y resuelve sus dudas con rapidez como parte de nuestra atención al huésped 24/7.')),
    dict(name='Juliana Marin', photo='juliana-marin',
         role=dict(en='Accounting & Finance Coordinator', es='Coordinadora de contabilidad y finanzas'),
         bio=dict(en='Juliana coordinates the monthly GAAP financial statements in the owner portal and owner payouts, made within the first 5 business days of each month, plus the bills we pay for Premium owners.',
                  es='Juliana coordina los estados financieros mensuales bajo GAAP del portal del propietario y los pagos a los propietarios, dentro de los primeros 5 días hábiles de cada mes, además de las cuentas que pagamos para los propietarios Premium.')),
    dict(name='Claudia Saenz', photo='claudia-saenz',
         role=dict(en='Head of the Legal Department', es='Directora del departamento legal'),
         bio=dict(en='Claudia leads the company\'s legal department, including the contracts and the registrations required to operate rentals in Colombia: RNT, SIRE and TRA.',
                  es='Claudia dirige el departamento legal de la empresa, incluidos los contratos y los registros necesarios para operar arriendos en Colombia: RNT, SIRE y TRA.')),
]
