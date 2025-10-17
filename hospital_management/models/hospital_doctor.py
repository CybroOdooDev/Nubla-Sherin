from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalDoctor(models.Model):
    _name = 'hospital.doctor'
    _description = 'Hospital Doctor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Doctor Name', required=True, tracking=True)
    doctor_id = fields.Char(string='Doctor ID', required=True, copy=False, readonly=True,
                            default=lambda self: _('New'))
    image = fields.Image(string='Photo', max_width=128, max_height=128)
    user_id = fields.Many2one('res.users', string='Related User', required=True)

    # Professional Information
    specialization = fields.Char(string='Specialization', required=True, tracking=True)
    qualification = fields.Text(string='Qualifications')
    license_number = fields.Char(string='License Number', tracking=True)
    experience_years = fields.Integer(string='Years of Experience')
    department_id = fields.Many2one('hospital.department', string='Department', required=True, tracking=True)

    # Contact Information
    email = fields.Char(string='Email', related='user_id.email', readonly=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')

    # Financial
    consultation_fee = fields.Float(string='Consultation Fee', required=True, tracking=True)
    follow_up_fee = fields.Float(string='Follow-up Fee')

    # Availability
    available_days = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Available Days', default='monday')

    start_time = fields.Float(string='Start Time', default=9.0)
    end_time = fields.Float(string='End Time', default=17.0)

    # Schedule Lines
    schedule_ids = fields.One2many('hospital.doctor.schedule', 'doctor_id', string='Weekly Schedule')

    # Relationships
    appointment_ids = fields.One2many('hospital.appointment', 'doctor_id', string='Appointments')
    consultation_ids = fields.One2many('hospital.consultation', 'doctor_id', string='Consultations')
    surgery_ids = fields.One2many('hospital.surgery', 'doctor_id', string='Surgeries')

    # Statistics
    appointment_count = fields.Integer(string='Appointments', compute='_compute_counts')
    consultation_count = fields.Integer(string='Consultations', compute='_compute_counts')
    patient_count = fields.Integer(string='Total Patients', compute='_compute_patient_count')

    # Status
    active = fields.Boolean(default=True, tracking=True)
    on_leave = fields.Boolean(string='On Leave', default=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('doctor_id', _('New')) == _('New'):
                vals['doctor_id'] = self.env['ir.sequence'].next_by_code('hospital.doctor') or _('New')
        return super(HospitalDoctor, self).create(vals_list)

    def _compute_counts(self):
        for record in self:
            record.appointment_count = len(record.appointment_ids)
            record.consultation_count = len(record.consultation_ids)

    def _compute_patient_count(self):
        for record in self:
            patients = record.consultation_ids.mapped('patient_id')
            record.patient_count = len(patients)

    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError(_('End time must be after start time.'))
            if record.start_time < 0 or record.end_time > 24:
                raise ValidationError(_('Time must be between 0 and 24 hours.'))

    def action_view_appointments(self):
        return {
            'name': _('Appointments'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.appointment',
            'view_mode': 'tree,form,calendar',
            'domain': [('doctor_id', '=', self.id)],
            'context': {'default_doctor_id': self.id}
        }

    def action_set_leave(self):
        self.on_leave = True

    def action_unset_leave(self):
        self.on_leave = False


class HospitalDoctorSchedule(models.Model):
    _name = 'hospital.doctor.schedule'
    _description = 'Doctor Schedule'
    _order = 'day_of_week'

    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True, ondelete='cascade')
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    slot_duration = fields.Integer(string='Slot Duration (minutes)', default=30)
    max_appointments = fields.Integer(string='Max Appointments', default=20)

    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError(_('End time must be after start time.'))