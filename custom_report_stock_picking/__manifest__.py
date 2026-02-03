# -*- coding: utf-8 -*-
################################################################################
#
#    Cats and Dogs Solution
#
#    Copyright (C) Cats and Dogs Solution.
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
################################################################################
{
    'name': "Custom Delivery Report",
    'version': '18.0.1.0.0',
    'category': ' ',
    'summary': 'Custom Delivery report',
    'author': 'Cats and Dogs Solutions',
    'company': 'Cats and Dogs Solutions',
    'maintainer': 'Cats and Dogs Solutions',
    'depends': ['stock','mrp','web','sale','account','sale_stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/report_deliveryslip.xml',
        'views/report_picking_operations.xml',
        'views/report_production_order.xml',
        'views/report_sale_order_document.xml',
        'views/report_templates.xml',
        'views/report_invoice_document.xml',
        'views/report_paper_format.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
