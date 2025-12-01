# -*- coding: utf-8 -*-
{
    'name': 'POS Rental Management',
    'summary': 'POS Rental Management',
    'description': 'POS Rental Management',
    'author': 'Nubla',
    'category': 'apps',
    'version': '19.0.1.1',
    'depends': ['base', 'sale', 'product', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_rental_menus.xml',
        'views/product_template.xml',
        'wizard/rental_tenure_wizard_view.xml',
        'views/pos_rental_res_config_settings_view.xml',

    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'pos_rental_management/static/src/app/popup/rental_popup.js',
            'pos_rental_management/static/src/app/popup/rental_popup.xml',
            'pos_rental_management/static/src/app/screens/product_screen/product_screen.js',

        ],
    },

    'application': True
}
