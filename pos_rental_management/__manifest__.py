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
        'views/rental_product_tenure_views.xml',
        'views/pos_rental_res_config_settings_view.xml',
        'views/pos_order_views.xml',
        'views/pos_config_views.xml'

    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'pos_rental_management/static/src/app/popup/rental_popup.js',
            'pos_rental_management/static/src/app/popup/rental_popup.xml',
            'pos_rental_management/static/src/app/models/rental_tenure.js',
            'pos_rental_management/static/src/app/screens/product_screen/product_screen.js',
            'pos_rental_management/static/src/app/popup/rent_configuration_popup.js',
            'pos_rental_management/static/src/app/popup/rent_configuration_popup.xml',
            'pos_rental_management/static/src/js/rented_details.js',
            'pos_rental_management/static/src/app/screens/partner_list/partner_rental_details_button.js',
            'pos_rental_management/static/src/xml/rented_details.xml',
            'pos_rental_management/static/src/xml/partner_list.xml',
            'pos_rental_management/static/src/css/rented_details.css',
            'pos_rental_management/static/src/app/screens/rented_orders/rented_orders_page.js',
            'pos_rental_management/static/src/app/screens/rented_orders/rented_orders_page.xml',
            'pos_rental_management/static/src/js/refund_return_popup.js',
            'pos_rental_management/static/src/xml/refund_return_popup.xml',
            'pos_rental_management/static/src/css/rental_badge.css',
            'pos_rental_management/static/src/overrides/models/pos_order_line.js',
            'pos_rental_management/static/src/overrides/components/pos_orderline.xml',
            'pos_rental_management/static/src/js/partial_payment_validation.js',
            'pos_rental_management/static/src/js/payment_screen_is_order_valid.js',
            # 'pos_rental_management/static/src/js/payment_screen_validate_patch.js',
            'pos_rental_management/static/src/xml/enable_validate_on_partial.xml',
            # 'pos_rental_management/static/src/js/payment_screen_button.js',
            # 'pos_rental_management/static/src/xml/payment_screen_button.xml',
            'pos_rental_management/static/src/js/order_finalize_partial_patch.js',
            'pos_rental_management/static/src/xml/receipt_partial_warning.xml'




        ],
    },

    'application': True
}
