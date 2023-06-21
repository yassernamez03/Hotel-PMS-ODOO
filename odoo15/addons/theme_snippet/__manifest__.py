# -*- coding: utf-8 -*-

{
    'name': 'Static Snippet',
    'description': 'my first static snippet',
    'version': '1.0',
    'author': 'Yasser Namez',
    'category': 'Theme/Creative',

    'depends': ['website'],
    'data': [
        'views/templates.xml',
        # 'views/options.xml',
    ],
    'assets': {
        'website.assets_frontend': [
            'theme_snippet/static/src/css/style.css',
        ]
    },
}