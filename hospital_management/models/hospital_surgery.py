from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalSurgery(models.Model):
    _name = 'hospital.surgery'
    _description = 'Hospital Surgery'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'surgery_date desc'

    # Basic Information
    name = fields.Char(string='Surgery Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Surgeon', required=True, tracking=True)
    admission_id = fields.Many2one('hospital.admission', string='Admission')

    # Surgery Details
    surgery_name = fields.Char(string='Surgery Name', required=True)
    surgery_type = fields.Selection([
        ('minor', 'Minor Surgery'),
        ('major', 'Major Surgery'),
        ('emergency', 'Emergency Surgery'),
    ], string='Surgery Type', required=True, default='minor')

    # Scheduling
    surgery_date = fields.Datetime(string='Surgery Date', required=True, tracking=True)
    duration = fields.Float(string='Duration (hours)', default=1.0)
    ot_id = fields.Many2one('hospital.operation.theater', string='Operation Theater',
                            required=True, tracking=True)

    # Team
    assistant_doctor_ids = fields.Many2many('hospital.doctor', 'surgery_assistant_rel',
                                            'surgery_id', 'doctor_id',
                                            string='Assistant Surgeons')
    anesthetist_id = fields.Many2one('hospital.doctor', string='Anesthetist')
    nurse_ids = fields.Many2many('res.users', 'surgery_nurse_rel',
                                 'surgery_id', 'user_id',
                                 string='Nursing Staff')

    # Pre-operative
    pre_operative_diagnosis = fields.Text(string='Pre-operative Diagnosis', required=True)
    pre_operative_notes = fields.Text(string='Pre-operative Notes')
    anesthesia_type = fields.Selection([
        ('general', 'General Anesthesia'),
        ('regional', 'Regional Anesthesia'),
        ('local', 'Local Anesthesia'),
        ('sedation', 'Sedation'),
    ], string='Anesthesia Type')

    # Intra-operative
    actual_start_time = fields.Datetime(string='Actual Start Time')
    actual_end_time = fields.Datetime(string='Actual End Time')
    actual_duration = fields.Float(string='Actual Duration', compute='_compute_actual_duration')
    procedure_performed = fields.Text(string='Procedure Performed')
    findings = fields.Text(string='Findings')
    complications = fields.Text(string='Complications')

    # Post-operative
    post_operative_diagnosis = fields.Text(string='Post-operative Diagnosis')
    post_operative_instructions = fields.Text(string='Post-operative Instructions')
    post_operative_notes = fields.Text(string='Post-operative Notes')

    # Equipment & Consumables
    equipment_ids = fields.Many2many('hospital.equipment', string='Equipment Used')
    consumable_ids = fields.One2many('hospital.surgery.consumable', 'surgery_id',
                                     string='Consumables Used')

    # Blood Transfusion
    blood_required = fields.Boolean(string='Blood Transfusion Required')
    blood_units = fields.Integer(string='Blood Units')
    blood_type = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('o+', 'O+'), ('o-', 'O-'),
        ('ab+', 'AB+'), ('ab-', 'AB-')
    ], string='Blood Type')

    # Status
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('pre_op', 'Pre-operative'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True)

    # Billing
    surgery_charge = fields.Float(string='Surgery Charge', required=True)
    ot_charge = fields.Float(string='OT Charge')
    anesthesia_charge = fields.Float(string='Anesthesia Charge')
    total_charge = fields.Float(string='Total Charge', compute='_compute_total_charge', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.surgery') or _('New')
        return super(HospitalSurgery, self).create(vals_list)

    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_actual_duration(self):
        for record in self:
            if record.actual_start_time and record.actual_end_time:
                delta = record.actual_end_time - record.actual_start_time
                record.actual_duration = delta.total_seconds() / 3600.0
            else:
                record.actual_duration = 0.0

    @api.depends('surgery_charge', 'ot_charge', 'anesthesia_charge', 'consumable_ids')
    def _compute_total_charge(self):
        for record in self:
            consumable_total = sum(record.consumable_ids.mapped('total'))
            record.total_charge = (record.surgery_charge + record.ot_charge +
                                   record.anesthesia_charge + consumable_total)

    def action_pre_op(self):
        self.write({'state': 'pre_op'})

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'actual_start_time': fields.Datetime.now(),
        })

    def action_complete(self):
        self.write({
            'state': 'completed',
            'actual_end_time': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class HospitalOperationTheater(models.Model):
    _name = 'hospital.operation.theater'
    _description = 'Operation Theater'

    name = fields.Char(string='OT Name', required=True)
    code = fields.Char(string='OT Code', required=True)
    floor_number = fields.Integer(string='Floor Number')

    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='available')

    # Equipment
    has_ventilator = fields.Boolean(string='Ventilator')
    has_monitor = fields.Boolean(string='Patient Monitor')
    has_anesthesia_machine = fields.Boolean(string='Anesthesia Machine')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)


class HospitalEquipment(models.Model):
    _name = 'hospital.equipment'
    _description = 'Hospital Equipment'

    name = fields.Char(string='Equipment Name', required=True)
    code = fields.Char(string='Equipment Code')
    category = fields.Char(string='Category')
    manufacturer = fields.Char(string='Manufacturer')

    # Maintenance
    last_maintenance = fields.Date(string='Last Maintenance')
    next_maintenance = fields.Date(string='Next Maintenance')

    active = fields.Boolean(default=True)


class HospitalSurgeryConsumable(models.Model):
    _name = 'hospital.surgery.consumable'
    _description = 'Surgery Consumable'

    surgery_id = fields.Many2one('hospital.surgery', string='Surgery', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True)
    total = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for record in self:
            record.total = record.quantity * record.unit_price