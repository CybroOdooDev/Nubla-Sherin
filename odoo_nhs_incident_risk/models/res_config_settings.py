from odoo import api, fields, models
import uuid


PROVIDER_TYPES = [
    ('nhs_trust', 'NHS Trust'),
    ('gp_practice', 'GP Practice / PCN'),
    ('care_home', 'Care Home'),
    ('domiciliary_care', 'Domiciliary Care'),
    ('independent_hospital', 'Independent Hospital'),
    ('hospice', 'Hospice'),
    ('pharmacy', 'Pharmacy'),
    ('dental', 'Dental Practice'),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    provider_type = fields.Selection(PROVIDER_TYPES, string='Provider Type',
                                     default='nhs_trust')
    public_form_enabled = fields.Boolean(string='Public Incident Report Form Enabled',
                                         default=True)
    public_form_token = fields.Char(string='Public Form Token', copy=False)
    anonymous_reporting_allowed = fields.Boolean(string='Allow Anonymous Reporting', default=True)
    doc_trigger_grade = fields.Selection([
        ('moderate', 'Moderate Harm'),
        ('severe', 'Severe Harm'),
        ('death', 'Death'),
    ], string='Duty of Candour Trigger Grade', default='moderate')
    default_handler_id = fields.Many2one('res.users', string='Default Incident Handler')
    board_pack_recipient_ids = fields.Many2many(
        'res.users', 'company_board_pack_recipients_rel',
        string='Board Pack Recipients')

    def _get_public_form_token(self):
        self.ensure_one()
        if not self.public_form_token:
            self.sudo().write({'public_form_token': str(uuid.uuid4()).replace('-', '')[:20]})
        return self.public_form_token


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    provider_type = fields.Selection(
        related='company_id.provider_type', readonly=False)
    public_form_enabled = fields.Boolean(
        related='company_id.public_form_enabled', readonly=False)
    public_form_token = fields.Char(
        related='company_id.public_form_token', readonly=True)
    anonymous_reporting_allowed = fields.Boolean(
        related='company_id.anonymous_reporting_allowed', readonly=False)
    doc_trigger_grade = fields.Selection(
        related='company_id.doc_trigger_grade', readonly=False)
    company_handler_id = fields.Many2one(
        related='company_id.default_handler_id', readonly=False)
    board_pack_recipient_ids = fields.Many2many(
        related='company_id.board_pack_recipient_ids', readonly=False)

    def action_regenerate_token(self):
        self.company_id.sudo().write(
            {'public_form_token': str(uuid.uuid4()).replace('-', '')[:20]})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
