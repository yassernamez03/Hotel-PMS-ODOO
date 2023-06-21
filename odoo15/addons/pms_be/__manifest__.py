{
    'name': 'BE Booking Engine',
    'summary': """
        This module adds a Booking Engine """,

    'description': """
        This module adds a Booking Engine 
    """,
    'author': "Agilorg",
    'website': "http://www.agilorg.com",
    'category': 'Property Management',
    'version': '15.0.1.0',
    'license': 'Other proprietary',
    'depends':  ['pms_be_data',
                ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/be_reservation_view.xml',
    ],

    'sequence': 3,
    'application': False,
    'price': 1500.00,
    'currency': 'EUR',


}
