from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalWard(models.Model):
    _name = 'hospital.ward'
    _description = 'Hospital Ward'
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Ward Name', required=True)
    code = fields.Char(string='Ward Code', required=True)
    department_id = fields.Many2one('hospital.department', string='Department')

    # Ward Details
    ward_type = fields.Selection([
        ('general', 'General Ward'),
        ('private', 'Private Room'),
        ('semi_private', 'Semi-Private'),
        ('icu', 'ICU'),
        ('nicu', 'NICU'),
        ('emergency', 'Emergency'),
        ('isolation', 'Isolation'),
    ], string='Ward Type', required=True)

    floor_number = fields.Integer(string='Floor Number')
    building = fields.Char(string='Building')

    # Capacity
    bed_ids = fields.One2many('hospital.bed', 'ward_id', string='Beds')
    total_beds = fields.Integer(string='Total Beds', compute='_compute_bed_stats', store=True)
    occupied_beds = fields.Integer(string='Occupied Beds', compute='_compute_bed_stats', store=True)
    available_beds = fields.Integer(string='Available Beds', compute='_compute_bed_stats', store=True)
    occupancy_rate = fields.Float(string='Occupancy Rate (%)', compute='_compute_bed_stats', store=True)

    # Facilities
    has_oxygen = fields.Boolean(string='Oxygen Supply')
    has_monitor = fields.Boolean(string='Patient Monitor')
    has_ventilator = fields.Boolean(string='Ventilator')

    # Charges
    daily_charge = fields.Float(string='Daily Charge')

    # Staff Assignment
    nurse_in_charge = fields.Many2one('res.users', string='Nurse In-Charge')

    # Status
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('bed_ids', 'bed_ids.state')
    def _compute_bed_stats(self):
        for record in self:
            record.total_beds = len(record.bed_ids)
            record.occupied_beds = len(record.bed_ids.filtered(lambda b: b.state == 'occupied'))
            record.available_beds = record.total_beds - record.occupied_beds
            if record.total_beds > 0:
                record.occupancy_rate = (record.occupied_beds / record.total_beds) * 100
            else:
                record.occupancy_rate = 0.0


class HospitalBed(models.Model):
    _name = 'hospital.bed'
    _description = 'Hospital Bed'
    _order = 'ward_id, bed_number'

    # Basic Information
    name = fields.Char(string='Bed Name', required=True)
    bed_number = fields.Char(string='Bed Number', required=True)
    ward_id = fields.Many2one('hospital.ward', string='Ward', required=True)

    # Bed Details
    bed_type = fields.Selection([
        ('standard', 'Standard Bed'),
        ('icu', 'ICU Bed'),
        ('ventilator', 'Ventilator Bed'),
        ('isolation', 'Isolation Bed'),
    ], string='Bed Type', required=True, default='standard')

    # Current Occupancy
    state = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved'),
    ], string='Status', default='available')

    current_patient_id = fields.Many2one('hospital.patient', string='Current Patient', readonly=True)
    current_admission_id = fields.Many2one('hospital.admission', string='Current Admission', readonly=True)

    # Features
    has_oxygen = fields.Boolean(string='Oxygen Supply')
    has_monitor = fields.Boolean(string='Patient Monitor')
    has_ventilator = fields.Boolean(string='Ventilator')

    # Capacity (for beds that can accommodate multiple patients in emergency)
    capacity = fields.Integer(string='Capacity', default=1)

    # Maintenance
    last_maintenance = fields.Date(string='Last Maintenance')
    next_maintenance = fields.Date(string='Next Maintenance')

    # Status
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('bed_number_unique', 'unique(bed_number, ward_id)',
         'Bed number must be unique within a ward!')
    ]

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_available(self):
        if self.current_patient_id:
            raise ValidationError(_('Cannot mark bed as available while patient is admitted.'))
        self.write({'state': 'available'})


class HospitalAdmission(models.Model):
    _name = 'hospital.admission'
    _description = 'Hospital Admission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'admission_date desc'

    # Basic Information
    name = fields.Char(string='Admission Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Attending Doctor', required=True, tracking=True)

    # Admission Details
    admission_date = fields.Datetime(string='Admission Date', required=True,
                                     default=fields.Datetime.now, tracking=True)
    admission_type = fields.Selection([
        ('emergency', 'Emergency'),
        ('elective', 'Elective'),
        ('transfer', 'Transfer'),
    ], string='Admission Type', required=True, default='elective')

    # Bed Assignment
    ward_id = fields.Many2one('hospital.ward', string='Ward', required=True, tracking=True)
    bed_id = fields.Many2one('hospital.bed', string='Bed', required=True,
                             domain="[('ward_id', '=', ward_id), ('state', '=', 'available')]",
                             tracking=True)

    # Medical Information
    diagnosis = fields.Text(string='Admission Diagnosis', required=True)
    chief_complaint = fields.Text(string='Chief Complaint')
    medical_history = fields.Text(string='Relevant Medical History')

    # Discharge Information
    discharge_date = fields.Datetime(string='Discharge Date', tracking=True)
    discharge_type = fields.Selection([
        ('normal', 'Normal Discharge'),
        ('against_advice', 'Against Medical Advice'),
        ('transfer', 'Transfer to Another Facility'),
        ('death', 'Death'),
    ], string='Discharge Type')
    discharge_diagnosis = fields.Text(string='Discharge Diagnosis')
    discharge_summary = fields.Html(string='Discharge Summary')
    discharge_instructions = fields.Text(string='Discharge Instructions')
    follow_up_date = fields.Date(string='Follow-up Date')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Duration
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)

    # Billing
    invoice_ids = fields.One2many('account.move', 'admission_id', string='Invoices')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount')

    # Related Records
    consultation_ids = fields.One2many('hospital.consultation', 'admission_id', string='Consultations')
    prescription_ids = fields.One2many('hospital.prescription', 'admission_id', string='Prescriptions')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.admission') or _('New')
        return super(HospitalAdmission, self).create(vals_list)

    @api.depends('admission_date', 'discharge_date')
    def _compute_duration(self):
        for record in self:
            if record.admission_date and record.discharge_date:
                delta = record.discharge_date - record.admission_date
                record.duration_days = delta.days
            else:
                record.duration_days = 0

    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.invoice_ids.mapped('amount_total'))

    @api.onchange('ward_id')
    def _onchange_ward_id(self):
        """Reset bed when ward changes"""
        self.bed_id = False

    def action_admit(self):
        """Admit patient and occupy bed"""
        for record in self:
            if record.bed_id.state != 'available':
                raise ValidationError(_('Selected bed is not available.'))

            record.bed_id.write({
                'state': 'occupied',
                'current_patient_id': record.patient_id.id,
                'current_admission_id': record.id,
            })

            record.write({'state': 'admitted'})

    def action_discharge(self):
        """Open discharge wizard"""
        return {
            'name': _('Discharge Patient'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.discharge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_admission_id': self.id}
        }

    def action_cancel(self):
        """Cancel admission and free bed"""
        for record in self:
            if record.bed_id:
                record.bed_id.write({
                    'state': 'available',
                    'current_patient_id': False,
                    'current_admission_id': False,
                })
            record.write({'state': 'cancelled'})

    def action_transfer_bed(self):
        """Transfer patient to another bed"""
        return {
            'name': _('Transfer Bed'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.bed.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_admission_id': self.id}
        }