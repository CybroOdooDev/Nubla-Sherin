# -*- coding: utf-8 -*-
import xmlrpc.client
from odoo import models, fields,api
from odoo.exceptions import ValidationError
import re

class TransferDataWizard(models.TransientModel):
    _name = 'transfer.data.wizard'
    _description = 'Transfer Data'

    url_db1 = fields.Char(String="Url")
    db_1 = fields.Char(String="Database name")
    username_db_1 = fields.Char(String="Username")
    password_db_1 = fields.Char(String="Password")

    @api.constrains('url_db1', 'db_1', 'username_db_1', 'password_db_1')
    def check_url(self):
        if not self.url_db1 == "http://localhost:8069":
            raise ValidationError("Url Enter Properly")
        elif not self.db_1 == "odoo17_migration":
            raise ValidationError("Enter Correct Database")
        elif not self.username_db_1 == "admin":
            raise ValidationError("Enter User Name of Database ")
        elif not self.password_db_1 == "cool":
            raise ValidationError("Enter Correct Password")


    def fetch_data(self):
        url_db1 = self.url_db1
        db_1 = self.db_1
        username_db_1 = self.username_db_1
        password_db_1 = self.password_db_1
        common_1 = xmlrpc.client.ServerProxy(f'{url_db1}/xmlrpc/2/common', allow_none=True)
        uid_db1 = common_1.authenticate(db_1, username_db_1, password_db_1, {})
        models_1 = xmlrpc.client.ServerProxy(f'{url_db1}/xmlrpc/2/object', allow_none=True)

        url_db2 = "http://localhost:8019"
        db_2 = "migration_18"
        username_db_2 = "admin"
        password_db_2 = "cool"
        common_2 = xmlrpc.client.ServerProxy(f'{url_db2}/xmlrpc/2/common', allow_none=True)
        uid_db2 = common_2.authenticate(db_2, username_db_2, password_db_2, {})
        models_2 = xmlrpc.client.ServerProxy(f'{url_db2}/xmlrpc/2/object', allow_none=True)
        partner_map = {}
        user_map = {}
        product_map = {}

        purchase_orders = models_1.execute_kw(
            db_1, uid_db1, password_db_1,
            'purchase.order', 'search_read',
            [[('state', '=', 'purchase')]],
            {'fields': [
                'name', 'date_approve', 'partner_id', 'user_id', 'origin',
                'amount_total', 'invoice_status', 'date_order', 'order_line','state'
            ]}
        )

        for po in purchase_orders:
            print("Processing PO:", po.get('name'))
            partner_id_src = po.get('partner_id')[0] if po.get('partner_id') else False
            partner_id_dest = False
            if partner_id_src:
                if partner_id_src in partner_map:
                    partner_id_dest = partner_map[partner_id_src]
                else:
                    partner_data = models_1.execute_kw(
                        db_1, uid_db1, password_db_1,
                        'res.partner', 'read', [partner_id_src], {'fields': ['name', 'email']}
                    )[0]
                    email = partner_data.get('email')
                    domain = [('email', '=', email)] if email else [('name', '=', partner_data['name'])]
                    existing_partner = models_2.execute_kw(
                        db_2, uid_db2, password_db_2, 'res.partner', 'search', [domain], {'limit': 1}
                    )
                    if existing_partner:
                        partner_id_dest = existing_partner[0]
                    else:
                        new_partner = {
                            'name': partner_data.get('name'),
                            'email': partner_data.get('email'),
                        }
                        partner_id_dest = models_2.execute_kw(
                            db_2, uid_db2, password_db_2, 'res.partner', 'create', [new_partner]
                        )
                    partner_map[partner_id_src] = partner_id_dest


            user_id_src = po.get('user_id')[0] if po.get('user_id') else False
            user_id_dest = False
            if user_id_src:
                if user_id_src in user_map:
                    user_id_dest = user_map[user_id_src]
                else:
                    user_data = models_1.execute_kw(
                        db_1, uid_db1, password_db_1,
                        'res.users', 'read', [user_id_src], {'fields': ['login', 'partner_id']}
                    )[0]
                    email = user_data.get('login')
                    existing_user = models_2.execute_kw(
                        db_2, uid_db2, password_db_2, 'res.users', 'search',
                        [[('login', '=', email)]], {'limit': 1}
                    )
                    if existing_user:
                        user_id_dest = existing_user[0]
                    else:
                        new_user = {
                            'login': email,
                            'partner_id': partner_id_dest,
                        }
                        user_id_dest = models_2.execute_kw(
                            db_2, uid_db2, password_db_2, 'res.users', 'create', [new_user]
                        )
                    user_map[user_id_src] = user_id_dest


            order_line_ids = po.get('order_line')
            if order_line_ids:
                order_lines = models_1.execute_kw(
                    db_1, uid_db1, password_db_1,
                    'purchase.order.line', 'read', [order_line_ids],
                    {'fields': ['product_id', 'product_qty', 'price_unit']}
                )
            po_origin = po.get('name')
            po_name= po.get('name')
            # print("orgin",po_origin)

            existing_po_ids = models_2.execute_kw(
                db_2, uid_db2, password_db_2,
                'purchase.order', 'search',
                [[('origin', '=', po_name)]],
                {'limit': 1}
            )

            if not existing_po_ids:
                new_po = {
                    'name': po.get('name'),
                    'date_approve': po.get('date_approve'),
                    'partner_id': partner_id_dest,
                    'user_id': user_id_dest,
                    'origin': po.get('name'),
                    'amount_total': po.get('amount_total'),
                    'invoice_status': po.get('invoice_status'),
                    'date_order': po.get('date_order'),
                    'state': po.get('state'),
                }
                print("Creating PO:", new_po)
                po_id_dest = models_2.execute_kw(
                    db_2, uid_db2, password_db_2,
                    'purchase.order', 'create', [new_po]
                )
                for line in order_lines:
                    product_id_src = line.get('product_id')[0] if line.get('product_id') else False
                    product_id_dest = product_map.get(product_id_src)
                    line_vals = {
                        'order_id': po_id_dest,
                        'product_id': product_id_dest,
                        'product_qty': line.get('product_qty'),
                        'price_unit': line.get('price_unit'),
                        'name': line.get('product_id')[1],
                    }
                    models_2.execute_kw(
                        db_2, uid_db2, password_db_2,
                        'purchase.order.line', 'create', [line_vals]
                    )
            else:
                print(f"Skipping PO with origin '{po_origin}' as it already exists.")
