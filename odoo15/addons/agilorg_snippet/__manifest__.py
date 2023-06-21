{
    'name': 'Agilorg Snippets',
    'description': 'Agilorg static Snippets',
    'version': '1.0',
    'author': 'Yasser Namez',
    'category': 'Tools',

    'depends': [],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        
        'data/room_board.xml',
        
        'views/Hotel.xml',
        'views/Snippets/product_details.xml',
        'views/Snippets/product.xml',
        'views/Snippets/rooms.xml',
        'views/Snippets/banner.xml',
        'views/Snippets/gallery.xml',
        'views/Snippets/title.xml',
        'views/Snippets/cover.xml',
        'views/Snippets/check_availability.xml',
        'views/Snippets/room_card.xml',
        
        'views/MyHotelviews/hotel_room.xml',
        'views/Data/rooms_avalibility.xml',
        'views/Data/template.xml',

    ],
    
    'assets': {
        'website.assets_frontend': [
            'odoo15/addons/agilorg_snippet/static/src/css/*',
            'odoo15/addons/agilorg_snippet/static/src/scss/*',
            'odoo15/addons/agilorg_snippet/static/src/js/*',
        ]
    },
}