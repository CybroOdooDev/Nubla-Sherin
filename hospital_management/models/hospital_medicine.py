from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class HospitalMedicine(models.Model):
    _name = 'hospital.medicine'
    _description = 'Hospital Medicine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Medicine Name', required=True, tracking=True)
    generic_name = fields.Char(string='Generic Name')
    medicine_code = fields.Char(string='Medicine Code', required=True, copy=False)

    # Category & Type
    category_id = fields.Many2one('hospital.medicine.category', string='Category')
    medicine_type = fields.Selection([
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('other', 'Other'),
    ], string='Type', required=True, default='tablet')

    # Manufacturer
    manufacturer = fields.Char(string='Manufacturer')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('is_company', '=', True)])

    # Strength & Composition
    strength = fields.Char(string='Strength', help='e.g., 500mg')
    composition = fields.Text(string='Composition')

    # Stock Information
    quantity_available = fields.Float(string='Available Quantity', tracking=True)
    unit_of_measure = fields.Selection([
        ('unit', 'Unit'),
        ('strip', 'Strip'),
        ('box', 'Box'),
        ('bottle', 'Bottle'),
    ], string='Unit of Measure', default='unit')

    min_stock_level = fields.Float(string='Minimum Stock Level', default=10)
    reorder_level = fields.Float(string='Reorder Level', default=20)

    # Batch Management
    batch_ids = fields.One2many('hospital.medicine.batch', 'medicine_id', string='Batches')

    # Pricing
    cost_price = fields.Float(string='Cost Price', required=True)
    sale_price = fields.Float(string='Sale Price', required=True)
    margin = fields.Float(string='Margin %', compute='_compute_margin', store=True)

    # Storage
    storage_condition = fields.Text(string='Storage Conditions')
    requires_prescription = fields.Boolean(string='Requires Prescription', default=True)
    controlled_substance = fields.Boolean(string='Controlled Substance')

    # Additional Information
    side_effects = fields.Text(string='Side Effects')
    contraindications = fields.Text(string='Contraindications')
    usage_instructions = fields.Text(string='Usage Instructions')

    # Status
    active = fields.Boolean(default=True)
    is_below_min_stock = fields.Boolean(string='Below Minimum Stock',
                                        compute='_compute_stock_status', store=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('cost_price', 'sale_price')
    def _compute_margin(self):
        for record in self:
            if record.cost_price > 0:
                record.margin = ((record.sale_price - record.cost_price) / record.cost_price) * 100
            else:
                record.margin = 0.0

    @api.depends('quantity_available', 'min_stock_level')
    def _compute_stock_status(self):
        for record in self:
            record.is_below_min_stock = record.quantity_available < record.min_stock_level

    @api.constrains('cost_price', 'sale_price')
    def _check_prices(self):
        for record in self:
            if record.cost_price < 0 or record.sale_price < 0:
                raise ValidationError(_('Prices cannot be negative.'))
            if record.sale_price < record.cost_price:
                raise ValidationError(_('Sale price cannot be less than cost price.'))

    def action_reorder(self):
        """Create purchase order for reordering"""
        # Logic to create purchase order
        pass

    def action_view_batches(self):
        return {
            'name': _('Batches'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.medicine.batch',
            'view_mode': 'tree,form',
            'domain': [('medicine_id', '=', self.id)],
            'context': {'default_medicine_id': self.id}
        }


class HospitalMedicineCategory(models.Model):
    _name = 'hospital.medicine.category'
    _description = 'Medicine Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code')
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('hospital.medicine.category', string='Parent Category')

    medicine_count = fields.Integer(string='Number of Medicines', compute='_compute_medicine_count')

    def _compute_medicine_count(self):
        for record in self:
            record.medicine_count = self.env['hospital.medicine'].search_count([
                ('category_id', '=', record.id)
            ])


class HospitalMedicineBatch(models.Model):
    _name = 'hospital.medicine.batch'
    _description = 'Medicine Batch'
    _order = 'expiry_date'

    medicine_id = fields.Many2one('hospital.medicine', string='Medicine', required=True, ondelete='cascade')
    batch_number = fields.Char(string='Batch Number', required=True)
    manufacturing_date = fields.Date(string='Manufacturing Date')
    expiry_date = fields.Date(string='Expiry Date', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    purchase_price = fields.Float(string='Purchase Price')

    is_expired = fields.Boolean(string='Expired', compute='_compute_expired', store=True)
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_days_to_expiry')

    @api.depends('expiry_date')
    def _compute_expired(self):
        today = date.today()
        for record in self:
            record.is_expired = record.expiry_date < today if record.expiry_date else False

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = date.today()
        for record in self:
            if record.expiry_date:
                delta = record.expiry_date - today
                record.days_to_expiry = delta.days
            else:
                record.days_to_expiry = 0

    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        for record in self:
            if record.expiry_date and record.manufacturing_date:
                if record.expiry_date <= record.manufacturing_date:
                    raise ValidationError(_('Expiry date must be after manufacturing date.'))

    @api.model
    def send_low_stock_alerts(self):
        """Send alerts for low stock medicines"""
        low_stock_medicines = self.search([('is_below_min_stock', '=', True)])

        if low_stock_medicines:
            # Get pharmacy manager
            pharmacy_group = self.env.ref('hospital_management.group_hospital_pharmacist')
            users = pharmacy_group.users

            for user in users:
                # Send notification
                self.env['mail.mail'].create({
                    'subject': 'Low Stock Alert - Hospital Pharmacy',
                    'body_html': self._get_low_stock_email_body(low_stock_medicines),
                    'email_to': user.email,
                }).send()

        return True

    def _get_low_stock_email_body(self, medicines):
        """Generate email body for low stock alert"""
        body = '<h3>Low Stock Medicines Alert</h3>'
        body += '<table border="1" style="border-collapse: collapse; width: 100%;">'
        body += '<tr><th>Medicine</th><th>Available</th><th>Min Level</th><th>Status</th></tr>'

        for medicine in medicines:
            body += f'<tr>'
            body += f'<td>{medicine.name}</td>'
            body += f'<td>{medicine.quantity_available}</td>'
            body += f'<td>{medicine.min_stock_level}</td>'
            body += f'<td style="color: red;">LOW STOCK</td>'
            body += f'</tr>'

        body += '</table>'
        return body

    @api.model
    def check_expired_medicines(self):
        """Check and alert for expired or near-expiry medicines"""
        today = date.today()
        warning_date = today + timedelta(days=30)  # 30 days warning

        # Get expired batches
        expired_batches = self.search([
            ('expiry_date', '<', today),
            ('quantity', '>', 0)
        ])

        # Get near-expiry batches
        near_expiry_batches = self.search([
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', warning_date),
            ('quantity', '>', 0)
        ])

        if expired_batches or near_expiry_batches:
            pharmacy_group = self.env.ref('hospital_management.group_hospital_pharmacist')
            users = pharmacy_group.users

            for user in users:
                self.env['mail.mail'].create({
                    'subject': 'Medicine Expiry Alert',
                    'body_html': self._get_expiry_alert_email(expired_batches, near_expiry_batches),
                    'email_to': user.email,
                }).send()

        return True

    def _get_expiry_alert_email(self, expired, near_expiry):
        """Generate expiry alert email"""
        body = '<h3>Medicine Expiry Alert</h3>'

        if expired:
            body += '<h4 style="color: red;">EXPIRED Medicines:</h4>'
            body += '<table border="1" style="border-collapse: collapse; width: 100%;">'
            body += '<tr><th>Medicine</th><th>Batch</th><th>Expiry Date</th><th>Quantity</th></tr>'
            for batch in expired:
                body += f'<tr style="background-color: #ffcccc;">'
                body += f'<td>{batch.medicine_id.name}</td>'
                body += f'<td>{batch.batch_number}</td>'
                body += f'<td>{batch.expiry_date}</td>'
                body += f'<td>{batch.quantity}</td>'
                body += f'</tr>'
            body += '</table><br/>'

        if near_expiry:
            body += '<h4 style="color: orange;">Near Expiry (30 days):</h4>'
            body += '<table border="1" style="border-collapse: collapse; width: 100%;">'
            body += '<tr><th>Medicine</th><th>Batch</th><th>Expiry Date</th><th>Days Left</th><th>Quantity</th></tr>'
            for batch in near_expiry:
                days_left = (batch.expiry_date - date.today()).days
                body += f'<tr style="background-color: #fff8cc;">'
                body += f'<td>{batch.medicine_id.name}</td>'
                body += f'<td>{batch.batch_number}</td>'
                body += f'<td>{batch.expiry_date}</td>'
                body += f'<td>{days_left}</td>'
                body += f'<td>{batch.quantity}</td>'
                body += f'</tr>'
            body += '</table>'

        return body
