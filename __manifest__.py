# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Transfering',
    'version': '18.0.1.0.0',
    'summary': 'Transfer Purchase Order Data from odoo17 to odoo18',
    'description': "This Odoo module, named Purchase Order Transferring facilitates the migration of purchase"
                   " order data from an Odoo 17 instance to a new Odoo 18 environment",
    'category': 'App',
    'author': 'Nubla',
    'depends': ['base','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
    ],
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': True,
    'application': False,
}