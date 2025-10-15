# -*- coding: utf-8 -*-
{
    'name': 'Product Snipptes',
    'summary': 'Product Snipptes',
    'description': 'This module is useto create Product Dynamic  Snippets',
    'author': 'Nubla',
    'category': 'apps',
    'version': '19.0.1.1',
    'depends': [
        'base',
        'website',
        'website_partner',
       'html_builder',
        'web',
        'website_mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_details.xml',
        'views/snippets/s_product.xml',
        'views/snippets/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'product_snippet/static/src/js/product_snippet.js',
        ],

    },
    'application': True,
    'license': 'LGPL-3',
}
