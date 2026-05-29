# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class NhsTrust(models.Model):
    _name = 'nhs.trust'
    _description = 'NHS Trust'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Trust Name', required=True, tracking=True, index=True)
    short_name = fields.Char(string='Short Name', tracking=True)
    ods_code = fields.Char(string='ODS Code', required=True, tracking=True, index=True)
    health_system = fields.Selection([
        ('nhs_england', 'NHS England'),
        ('nhs_scotland', 'NHS Scotland'),
    ], string='NHS Health System', required=True, default='nhs_england', tracking=True, index=True)
    trust_type_id = fields.Many2one('nhs.trust.type', string='Trust Type', required=True, tracking=True, index=True)
    foundation_trust = fields.Boolean(string='Foundation Trust', default=False, tracking=True)
    foundation_authorised_date = fields.Date(string='Foundation Authorisation Date', tracking=True)
    
    # Governance & Legal details
    companies_house_number = fields.Char(string='Companies House Number', tracking=True)
    vat_number = fields.Char(string='VAT Registration Number', tracking=True)
    establishment_date = fields.Date(string='Establishment Date', tracking=True)

    # Relationships & Geography
    region_id = fields.Many2one('nhs.region', string='NHS Region', required=True, index=True, tracking=True)
    icb_id = fields.Many2one('nhs.icb', string='Integrated Care Board (ICB)', index=True, tracking=True)
    ics_id = fields.Many2one('nhs.ics', string='Integrated Care System (ICS)', index=True, tracking=True)
    health_board_id = fields.Many2one('nhs.health.board', string='NHS Health Board', index=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Odoo Company Reference', default=lambda self: self.env.company, required=True, index=True)

    # Address & Contact info
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    county = fields.Char(string='County')
    zip = fields.Char(string='Postcode')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.uk', raise_if_not_found=False), required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')

    # Governance Leadership (Many2one -> res.partner)
    chair_id = fields.Many2one('res.partner', string='Board Chair', tracking=True, index=True)
    chief_executive_id = fields.Many2one('res.partner', string='Chief Executive', tracking=True, index=True)
    medical_director_id = fields.Many2one('res.partner', string='Medical Director', tracking=True, index=True)
    director_of_nursing_id = fields.Many2one('res.partner', string='Director of Nursing', tracking=True, index=True)
    finance_director_id = fields.Many2one('res.partner', string='Director of Finance', tracking=True, index=True)

    # Board Members List & State
    board_member_ids = fields.One2many('res.partner', 'nhs_trust_id', string='Board Members', domain=[('is_nhs_board_member', '=', True)])
    board_member_count = fields.Integer(string='Board Member Count', compute='_compute_board_member_count')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('active', 'Active'),
        ('special_measures', 'Special Measures'),
        ('merging', 'Merging'),
        ('dissolved', 'Dissolved'),
    ], string='Workflow State', required=True, default='draft', tracking=True, index=True)
    
    state_log_ids = fields.One2many('nhs.trust.state.log', 'trust_id', string='State Audit History')
    description = fields.Html(string='Description / Clinical Notes')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('ods_code_unique', 'unique(ods_code)', 'The ODS code must be unique!'),
    ]

    @api.constrains('ods_code')
    def _check_ods_code(self):
        for trust in self:
            if not trust.ods_code:
                continue
            code = trust.ods_code
            if not (3 <= len(code) <= 5):
                raise ValidationError('The ODS code must be between 3 and 5 characters long!')
            if not code.isalnum():
                raise ValidationError('The ODS code must contain alphanumeric characters only!')

    @api.constrains('health_system', 'icb_id', 'health_board_id', 'region_id')
    def _check_geographic_fields(self):
        for trust in self:
            if trust.region_id and trust.region_id.health_system != trust.health_system:
                raise ValidationError('The selected NHS Region must match the NHS Health System of this Trust!')
            
            if trust.health_system == 'nhs_england':
                if not trust.icb_id:
                    raise ValidationError('NHS Trusts in England must be associated with an Integrated Care Board (ICB)!')
                if trust.health_board_id:
                    raise ValidationError('An NHS England Trust cannot be associated with a Scottish Health Board!')
                if trust.icb_id.region_id != trust.region_id:
                    raise ValidationError('The selected ICB must belong to the selected NHS Region!')
                if trust.ics_id and trust.ics_id.icb_id != trust.icb_id:
                    raise ValidationError('The selected ICS subdivision must belong to the selected ICB!')
            
            elif trust.health_system == 'nhs_scotland':
                if not trust.health_board_id:
                    raise ValidationError('NHS Trusts in Scotland must be associated with a Health Board!')
                if trust.icb_id or trust.ics_id:
                    raise ValidationError('An NHS Scotland Trust cannot be associated with an English Integrated Care Board (ICB) or Integrated Care System (ICS)!')
                if trust.health_board_id.region_id != trust.region_id:
                    raise ValidationError('The selected Health Board must belong to the selected NHS Region!')

    @api.onchange('health_system')
    def _onchange_health_system(self):
        self.region_id = False
        self.icb_id = False
        self.ics_id = False
        self.health_board_id = False
        if self.health_system == 'nhs_england':
            return {'domain': {
                'region_id': [('health_system', '=', 'nhs_england')],
                'trust_type_id': [('health_system', 'in', ('nhs_england', 'both'))]
            }}
        elif self.health_system == 'nhs_scotland':
            return {'domain': {
                'region_id': [('health_system', '=', 'nhs_scotland')],
                'trust_type_id': [('health_system', 'in', ('nhs_scotland', 'both'))]
            }}

    @api.onchange('region_id')
    def _onchange_region_id(self):
        self.icb_id = False
        self.ics_id = False
        self.health_board_id = False
        if self.region_id:
            if self.health_system == 'nhs_england':
                return {'domain': {'icb_id': [('region_id', '=', self.region_id.id)]}}
            elif self.health_system == 'nhs_scotland':
                return {'domain': {'health_board_id': [('region_id', '=', self.region_id.id)]}}

    @api.onchange('icb_id')
    def _onchange_icb_id(self):
        self.ics_id = False
        domain = {'ics_id': [('id', '=', False)]}
        if self.icb_id:
            if self.icb_id.region_id:
                self.region_id = self.icb_id.region_id
            domain['ics_id'] = [('icb_id', '=', self.icb_id.id)]
            domain['region_id'] = [('id', '=', self.icb_id.region_id.id)]
        else:
            if self.health_system == 'nhs_england':
                domain['region_id'] = [('health_system', '=', 'nhs_england')]
        return {'domain': domain}

    @api.onchange('health_board_id')
    def _onchange_health_board_id(self):
        domain = {}
        if self.health_board_id:
            if self.health_board_id.region_id:
                self.region_id = self.health_board_id.region_id
            domain['region_id'] = [('id', '=', self.health_board_id.region_id.id)]
        else:
            if self.health_system == 'nhs_scotland':
                domain['region_id'] = [('health_system', '=', 'nhs_scotland')]
        return {'domain': domain}

    @api.depends('board_member_ids')
    def _compute_board_member_count(self):
        for trust in self:
            trust.board_member_count = len(trust.board_member_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'ods_code' in vals and vals['ods_code']:
                vals['ods_code'] = vals['ods_code'].upper()
        return super(NhsTrust, self).create(vals_list)

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('approved_state_change'):
            raise UserError('Direct updates to workflow state are blocked! Please use the "Change State" action button.')
        if 'ods_code' in vals and vals['ods_code']:
            vals['ods_code'] = vals['ods_code'].upper()
        return super(NhsTrust, self).write(vals)

    def action_open_state_change_wizard(self):
        self.ensure_one()
        return {
            'name': 'NHS Trust State Transition',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.trust.state.change.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('odoo_nhs_trust_management.view_nhs_trust_state_change_wizard_form').id,
            'target': 'new',
            'context': {
                'default_trust_id': self.id,
            }
        }
