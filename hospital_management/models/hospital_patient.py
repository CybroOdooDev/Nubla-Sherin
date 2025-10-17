from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class HospitalPatient(models.Model):
    _name = 'hospital.patient'
    _description = 'Hospital Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'

    # Basic Information
    name = fields.Char(string='Patient Name', required=True, tracking=True)
    patient_id = fields.Char(string='Patient ID', required=True, copy=False, readonly=True,
                             default=lambda self: _('New'))
    image = fields.Image(string='Photo', max_width=128, max_height=128)

    # Demographics
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True, tracking=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('o+', 'O+'), ('o-', 'O-'),
        ('ab+', 'AB+'), ('ab-', 'AB-')
    ], string='Blood Group', tracking=True)
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], string='Marital Status')

    # Contact Information
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone', required=True)
    mobile = fields.Char(string='Mobile')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # Emergency Contact
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relationship')

    # Medical Information
    allergies = fields.Text(string='Allergies')
    chronic_conditions = fields.Text(string='Chronic Conditions')
    current_medications = fields.Text(string='Current Medications')
    medical_history = fields.Html(string='Medical History')

    # Insurance
    insurance_id = fields.Many2one('hospital.insurance', string='Insurance')
    insurance_number = fields.Char(string='Insurance Number')
    insurance_expiry = fields.Date(string='Insurance Expiry')

    # Relationships
    appointment_ids = fields.One2many('hospital.appointment', 'patient_id', string='Appointments')
    consultation_ids = fields.One2many('hospital.consultation', 'patient_id', string='Consultations')
    prescription_ids = fields.One2many('hospital.prescription', 'patient_id', string='Prescriptions')
    admission_ids = fields.One2many('hospital.admission', 'patient_id', string='Admissions')
    invoice_ids = fields.One2many('account.move', 'patient_id', string='Invoices')

    # Statistics
    appointment_count = fields.Integer(string='Appointments', compute='_compute_counts')
    consultation_count = fields.Integer(string='Consultations', compute='_compute_counts')
    prescription_count = fields.Integer(string='Prescriptions', compute='_compute_counts')
    invoice_count = fields.Integer(string='Invoices', compute='_compute_counts')

    # Status
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    # Portal
    user_id = fields.Many2one('res.users', string='Portal User')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('patient_id', _('New')) == _('New'):
                vals['patient_id'] = self.env['ir.sequence'].next_by_code('hospital.patient') or _('New')
        return super(HospitalPatient, self).create(vals_list)

    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            if record.date_of_birth:
                today = date.today()
                record.age = today.year - record.date_of_birth.year - (
                        (today.month, today.day) < (record.date_of_birth.month, record.date_of_birth.day)
                )
            else:
                record.age = 0

    def _compute_counts(self):
        for record in self:
            record.appointment_count = len(record.appointment_ids)
            record.consultation_count = len(record.consultation_ids)
            record.prescription_count = len(record.prescription_ids)
            record.invoice_count = len(record.invoice_ids)

    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email:
                if not '@' in record.email:
                    raise ValidationError(_('Please enter a valid email address.'))

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for record in self:
            if record.date_of_birth and record.date_of_birth > date.today():
                raise ValidationError(_('Date of birth cannot be in the future.'))

    def action_view_appointments(self):
        return {
            'name': _('Appointments'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.appointment',
            'view_mode': 'tree,form,calendar',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id}
        }

    def action_view_consultations(self):
        return {
            'name': _('Consultations'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.consultation',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id}
        }

    def action_view_invoices(self):
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id, 'default_move_type': 'out_invoice'}
        }

    def create_portal_user(self):
        """Create portal user for patient"""
        for record in self:
            if not record.user_id and record.email:
                group_portal = self.env.ref('base.group_portal')
                user = self.env['res.users'].create({
                    'name': record.name,
                    'login': record.email,
                    'email': record.email,
                    'groups_id': [(6, 0, [group_portal.id])],
                    'partner_id': self.env['res.partner'].create({
                        'name': record.name,
                        'email': record.email,
                        'phone': record.phone,
                    }).id
                })
                record.user_id = user.id
                # Send invitation email
                user.action_reset_password()

    @api.model
    def get_dashboard_data(self):
        """Get dashboard statistics and data"""
        today = fields.Date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Patient statistics
        total_patients = self.search_count([])
        new_patients_today = self.search_count(
            [('create_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))])
        new_patients_week = self.search_count([('create_date', '>=', week_start)])
        new_patients_month = self.search_count([('create_date', '>=', month_start)])

        # Appointment statistics
        Appointment = self.env['hospital.appointment']
        appointments_today = Appointment.search([('appointment_date', '=', today)])
        total_appointments_today = len(appointments_today)
        appointments_confirmed = len(appointments_today.filtered(lambda a: a.state == 'confirmed'))
        appointments_waiting = len(appointments_today.filtered(lambda a: a.state == 'waiting'))
        appointments_completed = len(appointments_today.filtered(lambda a: a.state == 'completed'))

        # Today's appointments list
        today_appointments_list = []
        for apt in appointments_today[:10]:  # Limit to 10
            today_appointments_list.append({
                'id': apt.id,
                'patient_name': apt.patient_id.name,
                'doctor_name': apt.doctor_id.name,
                'appointment_time': apt.appointment_time,
                'state': apt.state,
            })

        # Doctor statistics
        Doctor = self.env['hospital.doctor']
        total_doctors = Doctor.search_count([])
        doctors_available = Doctor.search_count([('on_leave', '=', False)])
        doctors_on_leave = Doctor.search_count([('on_leave', '=', True)])

        # Bed statistics
        Bed = self.env['hospital.bed']
        total_beds = Bed.search_count([])
        beds_occupied = Bed.search_count([('state', '=', 'occupied')])
        beds_available = Bed.search_count([('state', '=', 'available')])
        occupancy_percentage = (beds_occupied / total_beds * 100) if total_beds > 0 else 0

        # Lab test statistics
        LabRequest = self.env['hospital.lab.request']
        pending_lab_tests = LabRequest.search_count([('state', 'in', ['requested', 'sample_collected', 'in_progress'])])
        completed_lab_tests_today = LabRequest.search_count([
            ('state', '=', 'completed'),
            ('completed_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))
        ])

        # Critical lab results
        critical_lab_results = []
        critical_labs = LabRequest.search([('is_critical', '=', True), ('state', '=', 'completed')], limit=5)
        for lab in critical_labs:
            critical_lab_results.append({
                'id': lab.id,
                'patient_name': lab.patient_id.name,
                'test_name': lab.test_id.name,
            })

        # Surgery statistics
        Surgery = self.env['hospital.surgery']
        pending_surgeries = Surgery.search_count([('state', 'in', ['scheduled', 'pre_op'])])
        completed_surgeries_today = Surgery.search_count([
            ('state', '=', 'completed'),
            ('actual_end_time', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))
        ])

        # Upcoming surgeries
        upcoming_surgeries_list = []
        upcoming_surgeries = Surgery.search([
            ('state', 'in', ['scheduled', 'pre_op']),
            ('surgery_date', '>=', fields.Datetime.now())
        ], order='surgery_date', limit=5)
        for surgery in upcoming_surgeries:
            upcoming_surgeries_list.append({
                'id': surgery.id,
                'patient_name': surgery.patient_id.name,
                'surgery_name': surgery.surgery_name,
                'surgery_date': surgery.surgery_date.strftime('%Y-%m-%d %H:%M') if surgery.surgery_date else '',
            })

        # Recent admissions
        Admission = self.env['hospital.admission']
        recent_admissions_list = []
        recent_admissions = Admission.search([('state', '=', 'admitted')], order='admission_date desc', limit=10)
        for admission in recent_admissions:
            recent_admissions_list.append({
                'id': admission.id,
                'patient_name': admission.patient_id.name,
                'ward_name': admission.ward_id.name,
                'bed_number': admission.bed_id.bed_number,
                'admission_date': admission.admission_date.strftime('%Y-%m-%d') if admission.admission_date else '',
                'state': admission.state,
            })

        # Low stock medicines
        Medicine = self.env['hospital.medicine']
        low_stock_medicines_list = []
        low_stock_medicines = Medicine.search([('is_below_min_stock', '=', True)], limit=10)
        for medicine in low_stock_medicines:
            low_stock_medicines_list.append({
                'id': medicine.id,
                'name': medicine.name,
                'quantity_available': medicine.quantity_available,
                'min_stock_level': medicine.min_stock_level,
            })

        # Revenue statistics (if account.move is available)
        Invoice = self.env['account.move']
        revenue_today = sum(Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '=', today)
        ]).mapped('amount_total'))

        revenue_week = sum(Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', week_start)
        ]).mapped('amount_total'))

        revenue_month = sum(Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', month_start)
        ]).mapped('amount_total'))

        return {
            'statistics': {
                'total_patients': total_patients,
                'new_patients_today': new_patients_today,
                'new_patients_week': new_patients_week,
                'new_patients_month': new_patients_month,
                'total_appointments_today': total_appointments_today,
                'appointments_confirmed': appointments_confirmed,
                'appointments_waiting': appointments_waiting,
                'appointments_completed': appointments_completed,
                'total_doctors': total_doctors,
                'doctors_available': doctors_available,
                'doctors_on_leave': doctors_on_leave,
                'total_beds': total_beds,
                'beds_occupied': beds_occupied,
                'beds_available': beds_available,
                'occupancy_percentage': occupancy_percentage,
                'pending_lab_tests': pending_lab_tests,
                'completed_lab_tests_today': completed_lab_tests_today,
                'pending_surgeries': pending_surgeries,
                'completed_surgeries_today': completed_surgeries_today,
                'revenue_today': revenue_today,
                'revenue_week': revenue_week,
                'revenue_month': revenue_month,
            },
            'today_appointments': today_appointments_list,
            'recent_admissions': recent_admissions_list,
            'critical_lab_results': critical_lab_results,
            'upcoming_surgeries': upcoming_surgeries_list,
            'low_stock_medicines': low_stock_medicines_list,
        }
