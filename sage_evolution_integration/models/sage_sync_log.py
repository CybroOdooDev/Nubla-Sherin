from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
from requests.auth import HTTPBasicAuth
import logging

_logger = logging.getLogger(__name__)

class SageSyncLog(models.Model):
    _name = 'sage.sync.log'
    _description = 'Sage Sync Log'
    _order = 'create_date desc'

    name = fields.Char(string='Action', default='Sync Operation')
    sync_date = fields.Datetime(string='Sync Date', default=fields.Datetime.now)
    status = fields.Selection([('success', 'Success'), ('error', 'Error')], string='Status')
    message = fields.Text(string='Message')

    # Dashboard / Progress Fields
    sync_contacts = fields.Boolean(string='Sync Contacts')
    sync_products = fields.Boolean(string='Sync Products')
    sync_sales_invoices = fields.Boolean(string='Sync Sales Invoices')
    sync_purchase_invoices = fields.Boolean(string='Sync Purchase Invoices')
    last_sync_date = fields.Datetime(string='Last Sync Date')
    
    connection_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected')
    ], string='Connection Status', compute='_compute_connection_status')

    def _compute_connection_status(self):
        for record in self:
            url = self.env['ir.config_parameter'].sudo().get_param('sage_evolution_integration.sage_api_url')
            record.connection_status = 'connected' if url else 'disconnected'

    def _get_freedom_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'url': (icp.get_param('sage_evolution_integration.sage_api_url') or '').rstrip('/'),
            'user': icp.get_param('sage_evolution_integration.sage_api_username'),
            'pwd': icp.get_param('sage_evolution_integration.sage_api_password'),
            'db': icp.get_param('sage_evolution_integration.sage_company_db'),
            'token': icp.get_param('sage_evolution_integration.sage_auth_token'),
        }

    def _call_freedom_api(self, endpoint, method='GET', data=None):
        """ Unified helper to call Sage API (Freedom or Cloud) """
        config = self._get_freedom_config()
        
        # Determine Auth Method
        auth = None
        headers = {}
        
        if config['token']:
            headers['Authorization'] = f"Bearer {config['token']}"
            _logger.info("Using Bearer Token for Sage API")
        elif config['user'] and config['pwd']:
            auth = HTTPBasicAuth(config['user'], config['pwd'])
            _logger.info("Using Basic Auth for Sage Freedom Service")
        else:
            raise UserError(_("Sage API not authenticated. Please check Settings."))

        # Determine URL
        if config['url']:
            url = f"{config['url']}/{endpoint.lstrip('/')}"
        else:
            # Fallback to a common Sage Cloud API base if no local URL is provided
            # This depends on the specific Sage product. 
            # Sage Business Cloud Accounting example:
            cloud_base = "https://api.columbus.sage.com/global/accounting/v3.1"
            url = f"{cloud_base}/{endpoint.lstrip('/')}"
        
        # Add DB to params for Freedom Service
        params = {}
        if config['db'] and not config['token']:
            params['DB'] = config['db']

        _logger.info("Calling Sage Freedom API: %s %s with params %s", method, url, params)
        try:
            response = requests.request(
                method,
                url,
                auth=auth,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            if response.status_code == 401:
                raise UserError(_("Authentication failed. Please check Sage Username and Password."))
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            _logger.error("HTTP Error calling Sage (%s): %s - %s", endpoint, e.response.status_code, e.response.text)
            raise UserError(_("Sage API HTTP Error: %s") % str(e))
        except requests.exceptions.RequestException as e:
            _logger.error("Sage Freedom API Request Error (%s): %s", endpoint, str(e))
            raise UserError(_("API Request Error: %s") % str(e))

    def action_execute_sync(self):
        """ Dashboard 'Execute' button logic """
        if self.sync_contacts:
            self.pull_customers()
        if self.sync_products:
            self.pull_products()
        if self.sync_sales_invoices:
            self.pull_sales_invoices()
        if self.sync_purchase_invoices:
            self.pull_purchase_invoices()
        
        self.last_sync_date = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Synchronization executed.',
                'type': 'success',
            }
        }

    def pull_customers(self):
        total_synced = 0
        try:
            data = self._call_freedom_api('Customers')
            # Freedom Service usually returns a list of dictionaries
            if not isinstance(data, list):
                data = [data] if data else []

            for item in data:
                # Sage Evolution usually uses 'ID' as primary key
                sage_id = str(item.get('ID') or item.get('Account'))
                partner = self.env['res.partner'].search([('sage_id', '=', sage_id)], limit=1)
                vals = {
                    'name': (item.get('Name') or item.get('Description') or item.get('Account') or 'Unknown').strip(),
                    'email': item.get('Email'),
                    'phone': item.get('Telephone'),
                    'sage_id': sage_id,
                    'sage_account_code': item.get('Account'),
                    'customer_rank': 1,
                    # Optional: handle addresses if available
                    'street': item.get('Address1'),
                    'street2': item.get('Address2'),
                    'city': item.get('Address3'),
                    'zip': item.get('PostCode'),
                    'vat': item.get('TaxNumber'),
                }
                if partner:
                    partner.write(vals)
                else:
                    self.env['res.partner'].create(vals)
                total_synced += 1

            self.create({'name': 'Pull Customers', 'status': 'success', 'message': f"Successfully synced {total_synced} customers."})
        except Exception as e:
            _logger.exception("Error during Pull Customers:")
            self.create({'name': 'Pull Customers', 'status': 'error', 'message': str(e)})

    def pull_products(self):
        total_synced = 0
        try:
            data = self._call_freedom_api('InventoryItems')
            if not isinstance(data, list):
                data = [data] if data else []

            for item in data:
                sage_id = str(item.get('ID'))
                product = self.env['product.template'].search([('sage_id', '=', sage_id)], limit=1)
                vals = {
                    'name': item.get('Description') or item.get('Code'),
                    'default_code': item.get('Code'),
                    'list_price': item.get('SellingPrice') or item.get('InclusivePrice') or 0.0,
                    'sage_id': sage_id,
                    'sage_code': item.get('Code'),
                    'type': 'consu', # Default to consumable if stock management is not fully synced
                }
                if product:
                    product.write(vals)
                else:
                    self.env['product.template'].create(vals)
                total_synced += 1

            self.create({'name': 'Pull Products', 'status': 'success', 'message': f"Successfully synced {total_synced} products."})
        except Exception as e:
            _logger.exception("Error during Pull Products:")
            self.create({'name': 'Pull Products', 'status': 'error', 'message': str(e)})

    def pull_sales_orders(self):
        total_synced = 0
        try:
            data = self._call_freedom_api('SalesOrders')
            if not isinstance(data, list):
                data = [data] if data else []

            for item in data:
                sage_id = str(item.get('ID'))
                order = self.env['sale.order'].search([('sage_id', '=', sage_id)], limit=1)
                if order:
                    continue
                
                # Try to find partner by sage_id or Account
                partner_sage_id = str(item.get('CustomerID') or item.get('AccountID'))
                partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1)
                if not partner:
                    _logger.warning("Partner with Sage ID %s not found for Order %s. Skipping.", partner_sage_id, item.get('OrderNumber'))
                    continue

                order_lines = []
                for line in item.get('Lines', []):
                    product_sage_id = str(line.get('InventoryItemID'))
                    product = self.env['product.product'].search([('sage_id', '=', product_sage_id)], limit=1)
                    if not product:
                        _logger.warning("Product with Sage ID %s not found for Order %s line. Creating minimal product.", product_sage_id, item.get('OrderNumber'))
                        # Minimal product creation could be done here, but better to skip or log
                    
                    order_lines.append((0, 0, {
                        'product_id': product.id if product else self.env.ref('product.product_product_4').id, # Fallback or skip
                        'name': line.get('Description') or 'Sage Line',
                        'product_uom_qty': float(line.get('Quantity') or 1.0),
                        'price_unit': float(line.get('UnitPrice') or 0.0),
                    }))

                vals = {
                    'partner_id': partner.id,
                    'sage_id': sage_id,
                    'sage_order_number': item.get('OrderNumber'),
                    'date_order': item.get('Date') or fields.Datetime.now(),
                    'order_line': order_lines,
                }
                self.env['sale.order'].create(vals)
                total_synced += 1
            
            self.create({'name': 'Pull Sales Orders', 'status': 'success', 'message': f"Successfully synced {total_synced} sales orders."})
        except Exception as e:
            _logger.exception("Error during Pull Sales Orders:")
            self.create({'name': 'Pull Sales Orders', 'status': 'error', 'message': str(e)})

    def pull_sales_invoices(self):
        total_synced = 0
        try:
            data = self._call_freedom_api('SalesInvoices')
            if not isinstance(data, list):
                data = [data] if data else []

            for item in data:
                sage_id = str(item.get('ID'))
                invoice = self.env['account.move'].search([('sage_id', '=', sage_id), ('move_type', '=', 'out_invoice')], limit=1)
                if invoice:
                    continue
                
                partner_sage_id = str(item.get('CustomerID') or item.get('AccountID'))
                partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1)
                if not partner:
                    _logger.warning("Partner with Sage ID %s not found for Invoice %s. Skipping.", partner_sage_id, item.get('InvoiceNumber'))
                    continue

                invoice_lines = []
                for line in item.get('Lines', []):
                    product_sage_id = str(line.get('InventoryItemID'))
                    product = self.env['product.product'].search([('sage_id', '=', product_sage_id)], limit=1)
                    
                    invoice_lines.append((0, 0, {
                        'product_id': product.id if product else False,
                        'name': line.get('Description') or 'Sage Line',
                        'quantity': float(line.get('Quantity') or 1.0),
                        'price_unit': float(line.get('UnitPrice') or 0.0),
                    }))

                vals = {
                    'move_type': 'out_invoice',
                    'partner_id': partner.id,
                    'sage_id': sage_id,
                    'sage_invoice_number': item.get('InvoiceNumber'),
                    'invoice_date': item.get('Date'),
                    'invoice_line_ids': invoice_lines,
                }
                self.env['account.move'].create(vals)
                total_synced += 1
            
            self.create({'name': 'Pull Sales Invoices', 'status': 'success', 'message': f"Successfully synced {total_synced} sales invoices."})
        except Exception as e:
            _logger.exception("Error during Pull Sales Invoices:")
            self.create({'name': 'Pull Sales Invoices', 'status': 'error', 'message': str(e)})

    def pull_purchase_invoices(self):
        total_synced = 0
        try:
            data = self._call_freedom_api('PurchaseInvoices')
            if not isinstance(data, list):
                data = [data] if data else []

            for item in data:
                sage_id = str(item.get('ID'))
                invoice = self.env['account.move'].search([('sage_id', '=', sage_id), ('move_type', '=', 'in_invoice')], limit=1)
                if invoice:
                    continue
                
                partner_sage_id = str(item.get('SupplierID'))
                partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1)
                if not partner:
                    _logger.warning("Supplier with Sage ID %s not found for Purchase Invoice %s. Skipping.", partner_sage_id, item.get('InvoiceNumber'))
                    continue

                invoice_lines = []
                for line in item.get('Lines', []):
                    product_sage_id = str(line.get('InventoryItemID'))
                    product = self.env['product.product'].search([('sage_id', '=', product_sage_id)], limit=1)
                    
                    invoice_lines.append((0, 0, {
                        'product_id': product.id if product else False,
                        'name': line.get('Description') or 'Sage Line',
                        'quantity': float(line.get('Quantity') or 1.0),
                        'price_unit': float(line.get('UnitPrice') or 0.0),
                    }))

                vals = {
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'sage_id': sage_id,
                    'sage_invoice_number': item.get('InvoiceNumber'),
                    'invoice_date': item.get('Date'),
                    'invoice_line_ids': invoice_lines,
                }
                self.env['account.move'].create(vals)
                total_synced += 1
            
            self.create({'name': 'Pull Purchase Invoices', 'status': 'success', 'message': f"Successfully synced {total_synced} purchase invoices."})
        except Exception as e:
            _logger.exception("Error during Pull Purchase Invoices:")
            self.create({'name': 'Pull Purchase Invoices', 'status': 'error', 'message': str(e)})

    def push_customers(self, partner_ids=None):
        """ Export customers to Sage Evolution """
        domain = [('sage_id', '=', False), ('customer_rank', '>', 0)]
        if partner_ids:
            domain = [('id', 'in', partner_ids)]
        
        partners = self.env['res.partner'].search(domain)
        success_count = 0
        for partner in partners:
            data = {
                'Name': partner.name,
                'Email': partner.email or '',
                'Telephone': partner.phone or '',
                # Add more fields as per Evolution schema
            }
            try:
                # POST to /Customers
                res_data = self._call_freedom_api('Customers', method='POST', data=data)
                if res_data and (res_data.get('ID') or res_data.get('Account')):
                    partner.write({'sage_id': str(res_data.get('ID') or res_data.get('Account'))})
                    success_count += 1
            except Exception as e:
                _logger.error("Sage Push Error: %s", str(e))

        self.create({'name': 'Push Customers', 'status': 'success', 'message': f"Successfully exported {success_count} customers."})

    def push_products(self):
        """ Export products to Sage Evolution """
        products = self.env['product.template'].search([('sage_id', '=', False)])
        success_count = 0
        for product in products:
            data = {
                'Description': product.name,
                'Code': product.default_code or '',
                'SellingPrice': product.list_price,
            }
            try:
                res_data = self._call_freedom_api('InventoryItems', method='POST', data=data)
                if res_data and res_data.get('ID'):
                    product.write({'sage_id': str(res_data.get('ID'))})
                    success_count += 1
            except Exception as e:
                _logger.error("Sage Push Error: %s", str(e))
        self.create({'name': 'Push Products', 'status': 'success', 'message': f"Successfully exported {success_count} products."})

    def push_sales_invoices(self):
        """ Export invoices to Sage Evolution """
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('sage_id', '=', False)])
        success_count = 0
        for invoice in invoices:
            if not invoice.partner_id.sage_id:
                continue
                
            lines = []
            for line in invoice.invoice_line_ids:
                lines.append({
                    'Description': line.name,
                    'Quantity': line.quantity,
                    'UnitPrice': line.price_unit,
                    'InventoryItemID': line.product_id.sage_id,
                })
            data = {
                'CustomerID': invoice.partner_id.sage_id,
                'Date': str(invoice.invoice_date),
                'InvoiceNumber': invoice.name,
                'Lines': lines,
            }
            try:
                res_data = self._call_freedom_api('SalesInvoices', method='POST', data=data)
                if res_data and res_data.get('ID'):
                    invoice.write({'sage_id': str(res_data.get('ID'))})
                    success_count += 1
            except Exception as e:
                _logger.error("Sage Push Error: %s", str(e))
        self.create({'name': 'Push Sales Invoices', 'status': 'success', 'message': f"Successfully exported {success_count} sales invoices."})
