from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalLabTest(models.Model):
    _name = 'hospital.lab.test'
    _description = 'Lab Test Catalog'
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Test Name', required=True)
    test_code = fields.Char(string='Test Code', required=True, copy=False)
    category_id = fields.Many2one('hospital.lab.test.category', string='Category')

    # Test Details
    description = fields.Text(string='Description')
    test_type = fields.Selection([
        ('blood', 'Blood Test'),
        ('urine', 'Urine Test'),
        ('stool', 'Stool Test'),
        ('imaging', 'Imaging'),
        ('biopsy', 'Biopsy'),
        ('culture', 'Culture'),
        ('other', 'Other'),
    ], string='Test Type', required=True)

    # Sample Information
    sample_type = fields.Char(string='Sample Type')
    sample_quantity = fields.Char(string='Sample Quantity Required')
    preparation_instructions = fields.Text(string='Preparation Instructions')

    # Processing
    processing_time = fields.Integer(string='Processing Time (hours)', default=24)
    department_id = fields.Many2one('hospital.department', string='Department')

    # Pricing
    price = fields.Float(string='Price', required=True)

    # Parameters
    parameter_ids = fields.One2many('hospital.lab.test.parameter', 'test_id', string='Test Parameters')

    # Status
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('test_code_unique', 'unique(test_code)', 'Test code must be unique!')
    ]


class HospitalLabTestCategory(models.Model):
    _name = 'hospital.lab.test.category'
    _description = 'Lab Test Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')


class HospitalLabTestParameter(models.Model):
    _name = 'hospital.lab.test.parameter'
    _description = 'Lab Test Parameter'

    test_id = fields.Many2one('hospital.lab.test', string='Test', required=True, ondelete='cascade')
    name = fields.Char(string='Parameter Name', required=True)
    unit = fields.Char(string='Unit')
    normal_range_min = fields.Float(string='Normal Range Min')
    normal_range_max = fields.Float(string='Normal Range Max')
    reference_range = fields.Char(string='Reference Range')


class HospitalLabRequest(models.Model):
    _name = 'hospital.lab.request'
    _description = 'Lab Test Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    # Basic Information
    name = fields.Char(string='Request Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Requested By', required=True, tracking=True)
    consultation_id = fields.Many2one('hospital.consultation', string='Consultation')

    # Request Details
    request_date = fields.Datetime(string='Request Date', required=True,
                                   default=fields.Datetime.now, tracking=True)
    test_id = fields.Many2one('hospital.lab.test', string='Test', required=True)
    priority = fields.Selection([
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    ], string='Priority', default='routine', required=True, tracking=True)

    # Sample Information
    sample_collected = fields.Boolean(string='Sample Collected', default=False)
    collection_date = fields.Datetime(string='Collection Date')
    collected_by = fields.Many2one('res.users', string='Collected By')
    sample_id = fields.Char(string='Sample ID')

    # Clinical Information
    clinical_notes = fields.Text(string='Clinical Notes')
    diagnosis = fields.Text(string='Provisional Diagnosis')

    # Results
    result_ids = fields.One2many('hospital.lab.result', 'request_id', string='Results')
    final_result = fields.Text(string='Final Result')
    interpretation = fields.Text(string='Interpretation')

    # Completion
    completed_date = fields.Datetime(string='Completed Date')
    completed_by = fields.Many2one('res.users', string='Completed By')
    verified_by = fields.Many2one('res.users', string='Verified By')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('sample_collected', 'Sample Collected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Critical Results
    is_critical = fields.Boolean(string='Critical Result', default=False)
    critical_alert_sent = fields.Boolean(string='Critical Alert Sent', default=False)

    # Billing
    invoice_id = fields.Many2one('account.move', string='Invoice')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.lab.request') or _('New')
        return super(HospitalLabRequest, self).create(vals_list)

    def action_request(self):
        self.write({'state': 'requested'})

    def action_collect_sample(self):
        self.write({
            'state': 'sample_collected',
            'sample_collected': True,
            'collection_date': fields.Datetime.now(),
            'collected_by': self.env.user.id,
        })

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
            'completed_by': self.env.user.id,
        })

        # Check for critical results
        if self.is_critical and not self.critical_alert_sent:
            self._send_critical_alert()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _send_critical_alert(self):
        """Send alert for critical results"""
        # Send notification to doctor
        self.doctor_id.user_id.notify_warning(
            message=_('Critical lab result for patient %s') % self.patient_id.name,
            title=_('Critical Lab Result')
        )
        self.critical_alert_sent = True

    def action_print_report(self):
        return self.env.ref('hospital_management.action_report_lab_result').report_action(self)


class HospitalLabResult(models.Model):
    _name = 'hospital.lab.result'
    _description = 'Lab Test Result'

    request_id = fields.Many2one('hospital.lab.request', string='Request', required=True, ondelete='cascade')
    parameter_id = fields.Many2one('hospital.lab.test.parameter', string='Parameter', required=True)

    # Result
    result_value = fields.Char(string='Result Value', required=True)
    unit = fields.Char(string='Unit', related='parameter_id.unit', readonly=True)
    reference_range = fields.Char(string='Reference Range', related='parameter_id.reference_range', readonly=True)

    # Status
    is_abnormal = fields.Boolean(string='Abnormal', default=False)
    is_critical = fields.Boolean(string='Critical', default=False)

    # Remarks
    remarks = fields.Text(string='Remarks')