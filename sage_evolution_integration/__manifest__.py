{
    'name': 'Sage Evolution Integration',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Integration with Sage 200 Evolution Freedom Service API',
    'description': """
        Sync data from Sage 200 Evolution to Odoo.
        - Customers Sync
        - Products Sync
        - Invoices Sync (with lines)
        - Sales Orders Sync
        - Configuration for Freedom Service API
    """,
    'author': 'Antigravity',
    'depends': ['base', 'contacts', 'stock', 'account', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sage_config_views.xml',
        'views/sage_config_views.xml',
        'views/sage_dashboard_views.xml',
        'views/res_partner_server_actions.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/sage_auth_templates.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
