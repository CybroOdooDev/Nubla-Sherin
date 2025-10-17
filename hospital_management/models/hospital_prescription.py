from odoo import models, fields, api, _
from datetime import datetime, timedelta


class HospitalPrescription(models.Model):
    _name = 'hospital.prescription'
    _description = 'Hospital Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc'

    # Basic Information
    name = fields.Char(string='Prescription Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True, tracking=True)
    consultation_id = fields.Many2one('hospital.consultation', string='Consultation')
    admission_id = fields.Many2one('hospital.admission', string="Admission")


    # Prescription Details
    prescription_date = fields.Datetime(string='Prescription Date', required=True,
                                        default=fields.Datetime.now, tracking=True)


    # Prescription Lines
    prescription_line_ids = fields.One2many('hospital.prescription.line', 'prescription_id',
                                            string='Medicines')

    # Additional Information
    diagnosis = fields.Text(string='Diagnosis')
    notes = fields.Text(string='Special Instructions')

    # Validity
    valid_from = fields.Date(string='Valid From', default=fields.Date.today)
    valid_to = fields.Date(string='Valid To')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('prescribed', 'Prescribed'),
        ('dispensed', 'Dispensed'),
        ('partially_dispensed', 'Partially Dispensed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Dispensing
    dispensed_by = fields.Many2one('res.users', string='Dispensed By')
    dispensed_date = fields.Datetime(string='Dispensed Date')

    # Billing
    invoice_id = fields.Many2one('account.move', string='Invoice')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.prescription') or _('New')
        return super(HospitalPrescription, self).create(vals_list)

    def action_prescribe(self):
        self.write({'state': 'prescribed'})

    def action_dispense(self):
        """Dispense medicines and update stock"""
        for record in self:
            for line in record.prescription_line_ids:
                if line.medicine_id:
                    # Update medicine stock
                    line.medicine_id.quantity_available -= line.quantity

            record.write({
                'state': 'dispensed',
                'dispensed_by': self.env.user.id,
                'dispensed_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_print_prescription(self):
        return self.env.ref('hospital_management.action_report_prescription').report_action(self)


class HospitalPrescriptionLine(models.Model):
    _name = 'hospital.prescription.line'
    _description = 'Prescription Line'

    prescription_id = fields.Many2one('hospital.prescription', string='Prescription',
                                      required=True, ondelete='cascade')
    medicine_id = fields.Many2one('hospital.medicine', string='Medicine', required=True)

    # Dosage
    quantity = fields.Integer(string='Quantity', required=True, default=1)
    dosage = fields.Char(string='Dosage', required=True, help='e.g., 1 tablet')
    frequency = fields.Selection([
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('thrice_daily', 'Thrice Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('as_needed', 'As Needed'),
        ('custom', 'Custom'),
    ], string='Frequency', required=True, default='once_daily')
    custom_frequency = fields.Char(string='Custom Frequency')

    # Duration
    duration = fields.Integer(string='Duration (days)', default=7)

    # Instructions
    before_food = fields.Boolean(string='Before Food')
    after_food = fields.Boolean(string='After Food')
    special_instructions = fields.Text(string='Special Instructions')

    # Computed
    total_quantity = fields.Integer(string='Total Quantity', compute='_compute_total_quantity', store=True)
    unit_price = fields.Float(string='Unit Price', related='medicine_id.sale_price', readonly=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'duration', 'frequency')
    def _compute_total_quantity(self):
        frequency_map = {
            'once_daily': 1,
            'twice_daily': 2,
            'thrice_daily': 3,
            'four_times_daily': 4,
        }
        for record in self:
            freq = frequency_map.get(record.frequency, 1)
            record.total_quantity = record.quantity * freq * record.duration

    @api.depends('total_quantity', 'unit_price')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.total_quantity * record.unit_price