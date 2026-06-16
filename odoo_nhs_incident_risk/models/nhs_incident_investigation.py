from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class NhsInvestigation(models.Model):
    _name = 'nhs.investigation'
    _description = 'Investigation / Learning Response (PSIRF-aligned)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New')
    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict')
    response_level = fields.Selection([
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'PSII — Patient Safety Incident Investigation'),
    ], string='Response Level', required=True, tracking=True)
    lead_investigator_id = fields.Many2one('res.users', string='Lead Investigator',
                                           required=True, tracking=True)
    team_member_ids = fields.Many2many('res.users', string='Team Members / Panel')
    terms_of_reference = fields.Text(string='Terms of Reference',
                                     help='Required for PSII-level investigations.')
    timeline_ids = fields.One2many('nhs.investigation.timeline', 'investigation_id',
                                   string='Chronology')
    contributing_factor_ids = fields.Many2many('nhs.contributing.factor',
                                               string='Contributing Factors')
    findings = fields.Text(string='Findings')
    lessons_learned = fields.Text(string='Lessons Learned')
    good_practice = fields.Text(string='Areas of Good Practice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', required=True, tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    approved_at = fields.Datetime(string='Approved At')
    action_ids = fields.One2many('nhs.action', 'investigation_id', string='Actions')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.investigation') or 'New'
        return super().create(vals_list)

    @api.constrains('response_level', 'terms_of_reference')
    def _check_psii_tor(self):
        for rec in self:
            if rec.response_level == 'psii' and rec.state != 'draft' \
               and not rec.terms_of_reference:
                raise ValidationError('Terms of Reference are required for PSII investigations.')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit(self):
        for rec in self:
            if rec.response_level == 'psii' and not rec.terms_of_reference:
                raise UserError('Terms of Reference must be completed before submission.')
            if not rec.findings:
                raise UserError('Findings must be recorded before submission.')
        self.write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can approve investigations.')
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_at': fields.Datetime.now(),
        })

    def action_rework(self):
        self.write({'state': 'in_progress'})

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'odoo_nhs_incident_risk.action_report_investigation_summary'
        ).report_action(self)
