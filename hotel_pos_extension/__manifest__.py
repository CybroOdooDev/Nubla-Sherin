# -*- coding: utf-8 -*-
{
    'name': 'Hotel POS Extension',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Hotel Room Charge from POS',
    'description': """This module allows charging POS orders directly to hotel folios.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['point_of_sale', 'hotel_management_odoo'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
        'views/pos_order_views.xml',
        'views/room_booking_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'hotel_pos_extension/static/src/js/**/*',
            'hotel_pos_extension/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
