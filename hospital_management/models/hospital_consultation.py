from odoo import models, fields, api, _


class HospitalConsultation(models.Model):
    _name = 'hospital.consultation'
    _description = 'Hospital Consultation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'consultation_date desc'

    # Basic Information
    name = fields.Char(string='Consultation Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True, tracking=True)
    appointment_id = fields.Many2one('hospital.appointment', string='Appointment')

    # Consultation Details

    admission_id = fields.Many2one('hospital.admission', string='Admission')
    consultation_date = fields.Datetime(string='Consultation Date', required=True,
                                        default=fields.Datetime.now, tracking=True)
    consultation_type = fields.Selection([
        ('new', 'New Patient'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
    ], string='Type', required=True, default='new')

    # Vitals
    temperature = fields.Float(string='Temperature (°F)')
    blood_pressure_systolic = fields.Integer(string='BP Systolic')
    blood_pressure_diastolic = fields.Integer(string='BP Diastolic')
    pulse = fields.Integer(string='Pulse Rate')
    respiratory_rate = fields.Integer(string='Respiratory Rate')
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    oxygen_saturation = fields.Float(string='SpO2 (%)')

    # Medical Information
    chief_complaint = fields.Text(string='Chief Complaint', required=True)
    history_present_illness = fields.Text(string='History of Present Illness')
    physical_examination = fields.Text(string='Physical Examination')

    # Diagnosis
    diagnosis = fields.Text(string='Diagnosis', required=True)
    icd10_code = fields.Char(string='ICD-10 Code')
    provisional_diagnosis = fields.Text(string='Provisional Diagnosis')
    differential_diagnosis = fields.Text(string='Differential Diagnosis')

    # Treatment
    treatment_plan = fields.Text(string='Treatment Plan')
    advice = fields.Text(string='Advice')
    follow_up_date = fields.Date(string='Follow-up Date')
    follow_up_instructions = fields.Text(string='Follow-up Instructions')

    # Related Records
    prescription_ids = fields.One2many('hospital.prescription', 'consultation_id', string='Prescriptions')
    lab_request_ids = fields.One2many('hospital.lab.request', 'consultation_id', string='Lab Requests')

    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # Progress Notes
    progress_notes = fields.Text(string='Progress Notes')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    # Billing
    invoice_id = fields.Many2one('account.move', string='Invoice')
    is_invoiced = fields.Boolean(string='Invoiced', default=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.consultation') or _('New')
        return super(HospitalConsultation, self).create(vals_list)

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for record in self:
            if record.weight and record.height:
                height_m = record.height / 100.0
                record.bmi = record.weight / (height_m * height_m)
            else:
                record.bmi = 0.0

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_create_prescription(self):
        return {
            'name': _('Create Prescription'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.prescription',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            }
        }

    def action_request_lab_test(self):
        return {
            'name': _('Request Lab Test'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.lab.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            }
        }

    def action_create_invoice(self):
        """Create invoice for consultation"""
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.id,
            'patient_id': self.patient_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f'Consultation - {self.doctor_id.name}',
                'quantity': 1,
                'price_unit': self.doctor_id.consultation_fee,
            })],
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.write({
            'invoice_id': invoice.id,
            'is_invoiced': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }