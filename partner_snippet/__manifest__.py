# -*- coding: utf-8 -*-
{
    'name': 'Partners Snipptes',
    'summary': 'Dynamic Snipptes',
    'description': 'This module is useto create Dynamic Snippets',
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
        'views/snippets/partner_snippet_views.xml',
        'views/snippets/snipptes.xml',
        'views/snippets/s_partner.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'partner_snippet/static/src/js/partner_snippet.js',
            'partner_snippet/static/src/xml/partner_template_views.xml',
            'partner_snippet/static/src/snippets/**/*.js',
        ],
        'website.website_builder_assets': [

        ],
    },
    'application': True,
    'license': 'LGPL-3',
}
