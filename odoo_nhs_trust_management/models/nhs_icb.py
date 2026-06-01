# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NhsIcb(models.Model):
    _name = 'nhs.icb'
    _description = 'NHS Integrated Care Board (ICB)'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
        tracking=True,
        help="Full statutory name (e.g. 'NHS North East and North Cumbria ICB'). Tracked on chatter."
    )
    code = fields.Char(
        string='ODS Code',
        required=True,
        index=True,
        help="Official NHS Digital ODS code for the ICB (e.g. 'QHM', 'QOQ'). Must be unique. "
             "Used in NHS-internal reporting and matches the codes published on NHS Digital ODS portal."
    )
    short_name = fields.Char(
        string='Short Name',
        help="Optional short display name shown in tight spaces (kanban cards, narrow columns)."
    )
    region_id = fields.Many2one(
        'nhs.region',
        string='NHS Region',
        required=True,
        index=True,
        domain="[('health_system', '=', 'nhs_england')]",
        help="Parent NHS England region. Domain restricts to regions with health_system='nhs_england'."
    )
    ics_ids = fields.One2many(
        'nhs.ics',
        'icb_id',
        string='ICS Subdivisions',
        help="Child Integrated Care Systems. An ICB may have multiple ICSs as sub-divisions."
    )
    trust_ids = fields.One2many(
        'nhs.trust',
        'icb_id',
        string='Associated Trusts',
        help="All Trusts whose `icb_id` points at this ICB."
    )
    trust_count = fields.Integer(
        string='Trusts',
        compute='_compute_trust_count',
        help="Auto-computed count of linked trusts. `@api.depends('trust_ids')`. Used on the stat button."
    )
    population_served = fields.Integer(
        string='Population Served',
        help="Total population the ICB plans services for. Used in regional reporting and benchmarking."
    )
    headquarters_address = fields.Text(
        string='Headquarters Address',
        help="Free-text HQ address. Plain text deliberately — not used in mailing logic, "
             "so no need for structured address fields."
    )
    website = fields.Char(
        string='Website',
        help="Public ICB website URL. Rendered with `widget='url'` in views."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The ICB ODS code must be unique!'),
    ]

    @api.constrains('region_id')
    def _check_region_system(self):
        for icb in self:
            if icb.region_id and icb.region_id.health_system != 'nhs_england':
                raise ValidationError(
                    'An Integrated Care Board (ICB) must belong to an NHS England region.'
                )

    @api.depends('trust_ids')
    def _compute_trust_count(self):
        for icb in self:
            icb.trust_count = len(icb.trust_ids)

    def action_view_trusts(self):
        """Opens the Trust list filtered by this ICB."""
        self.ensure_one()
        return {
            'name': 'Trusts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.trust',
            'view_mode': 'list,form',
            'domain': [('icb_id', '=', self.id)],
            'context': {'default_icb_id': self.id},
        }
