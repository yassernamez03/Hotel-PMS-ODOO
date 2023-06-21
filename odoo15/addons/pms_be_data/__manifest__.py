{
    'name': 'BE Booking Engine',
    'summary': """
        This module adds a Booking Engine Data""",

    'description': """
        This module adds a Booking Engine Data
    """,
    'author': "Agilorg",
    'website': "http://www.agilorg.com",
    'category': 'Property Management',
    'version': '15.0.1.0',
    'license': 'Other proprietary',
    'depends':  ['base', 'mail', 'account', 'stock',
                'sale_stock',
                'product',
                'contacts',
                'partner_firstname',
                'base_address_city',
               ],
    'data': [
        'security/be_security.xml',
        'security/ir.model.access.csv',
        'data/be_board.xml',
        'data/product_category.xml',
        'data/product_product.xml',
        'data/res_country_state_data.xml',
        'data/res_city.xml',
        'data/res_city_district.xml',
        'data/res_partner_category.xml',

        'views/inherited_res_city.xml',
        'views/partner_district_view.xml',
        'views/res_partner_view.xml',
        'views/be_board_view.xml',
        'views/be_room_type_views.xml',
        'views/be_taxes_view.xml',
        'views/be_hotel_views.xml',
        'views/be_rate_plan_views.xml',
        'views/be_room_type_availability_views.xml',
        'views/menu_action.xml',
    ],

    'sequence': 3,
    'application': False,
    'price': 1500.00,
    'currency': 'MAD',


}
