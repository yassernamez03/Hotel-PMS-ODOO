# -*- coding: utf-8 -*-
{
    'name': "My Library",  # Module title
    'summary': "Manage books easily",  # Module subtitle phrase
    'description': """
Manage Library
==============
Description related to library.
    """,  # Supports reStructuredText(RST) format
    'author': "Parth Gajjar",
    'website': "http://www.example.com",
    'category': 'Tools',
    'version': '14.0.1',
    'depends': ['base', 'website'],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/library_book.xml',
        'views/templates.xml',
        'views/snippets.xml'
    ],

    # 'assets': {
    #     'website.assets_frontend': [
    #         '/my_library/static/src/js/Snippets.js',
    #     ]
    # },
}



