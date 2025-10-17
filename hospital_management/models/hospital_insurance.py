from odoo import models, fields, api, _


class HospitalInsurance(models.Model):
    _name = 'hospital.insurance'
    _description = 'Hospital Insurance'
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Insurance Company', required=True)
    code = fields.Char(string='Insurance Code')

    # Contact Information
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')

    # Address
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # Coverage Details
    coverage_percentage = fields.Float(string='Coverage %', default=100.0)
    max_coverage_amount = fields.Float(string='Maximum Coverage Amount')

    # Plans
    plan_ids = fields.One2many('hospital.insurance.plan', 'insurance_id', string='Insurance Plans')

    # Status
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)


class HospitalInsurancePlan(models.Model):
    _name = 'hospital.insurance.plan'
    _description = 'Insurance Plan'

    name = fields.Char(string='Plan Name', required=True)
    insurance_id = fields.Many2one('hospital.insurance', string='Insurance Company', required=True)

    # Coverage
    coverage_percentage = fields.Float(string='Coverage %', default=100.0)
    max_coverage_amount = fields.Float(string='Maximum Coverage Amount')
    deductible = fields.Float(string='Deductible')
    copay_percentage = fields.Float(string='Co-pay %')

    # Services Covered
    covers_consultation = fields.Boolean(string='Consultation', default=True)
    covers_lab = fields.Boolean(string='Lab Tests', default=True)
    covers_pharmacy = fields.Boolean(string='Pharmacy', default=True)
    covers_surgery = fields.Boolean(string='Surgery', default=True)
    covers_admission = fields.Boolean(string='Admission', default=True)

    active = fields.Boolean(default=True)


class HospitalInsuranceClaim(models.Model):
    _name = 'hospital.insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'claim_date desc'

    # Basic Information
    name = fields.Char(string='Claim Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True)
    insurance_id = fields.Many2one('hospital.insurance', string='Insurance Company', required=True)
    plan_id = fields.Many2one('hospital.insurance.plan', string='Insurance Plan')

    # Claim Details
    claim_date = fields.Date(string='Claim Date', required=True, default=fields.Date.today)
    service_date = fields.Date(string='Service Date', required=True)

    # Amounts
    claimed_amount = fields.Float(string='Claimed Amount', required=True)
    approved_amount = fields.Float(string='Approved Amount')
    deductible = fields.Float(string='Deductible')
    copay = fields.Float(string='Co-pay')
    paid_amount = fields.Float(string='Paid Amount')

    # Related Records
    invoice_id = fields.Many2one('account.move', string='Invoice')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.insurance.claim') or _('New')
        return super(HospitalInsuranceClaim, self).create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})