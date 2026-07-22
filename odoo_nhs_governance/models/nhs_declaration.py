# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NhsDeclaration(models.Model):
    _name = 'nhs.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Declaration of Interest'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        help="Display name built from the director and declaration type.",
    )
    director_id = fields.Many2one(
        'nhs.director',
        required=True,
        tracking=True,
        help="Director or officer making the declaration.",
    )
    company_id = fields.Many2one(
        related='director_id.company_id',
        store=True,
        help="Owning company inherited from the director.",
    )
    category_id = fields.Many2one(
        'nhs.governance.interest.category',
        string='Interest Category',
        help="Configured interest category for reporting and published registers.",
    )
    declaration_type = fields.Selection([
        ('financial', 'Financial'),
        ('non_financial_professional', 'Non-Financial Professional'),
        ('non_financial_personal', 'Non-Financial Personal'),
        ('loyalty', 'Loyalty'),
        ('indirect', 'Indirect'),
        ('nil', 'Nil Return'),
    ], required=True, default='nil', tracking=True,
        help="Type of declared interest, including nil returns where no interests exist.")
    nature = fields.Text(help="Description of the interest and why it may be relevant.")
    related_org = fields.Char(string='Related Organisation', help="Organisation the interest relates to.")
    value_band = fields.Char(help="Value band or benefit range where relevant for financial interests.")
    date_from = fields.Date(help="Start date of the declared interest.")
    date_to = fields.Date(help="End date of the declared interest, if known.")
    event = fields.Selection([
        ('appointment', 'On Appointment'),
        ('annual', 'Annual Refresh'),
        ('at_meeting', 'At Meeting'),
        ('ad_hoc', 'Ad-hoc'),
    ], default='annual', required=True,
        help="Declaration trigger: appointment, annual refresh, at-meeting declaration or ad-hoc update.")
    meeting_id = fields.Many2one(
        'nhs.meeting',
        help="Meeting where this declaration was made, for at-meeting declarations.",
    )
    agenda_item_id = fields.Many2one(
        'nhs.agenda.item',
        help="Specific agenda item affected by the declared conflict.",
    )
    conflict_management = fields.Selection([
        ('noted', 'Noted'),
        ('withdrew_from_item', 'Withdrew From Item'),
        ('left_room', 'Left The Room'),
        ('no_action', 'No Action Required'),
    ], default='no_action', help="How the conflict was managed during the meeting or item.")
    is_published = fields.Boolean(
        string='Published Register',
        help="Include this declaration in the curated published declaration-of-interest register.",
    )
    active = fields.Boolean(default=True, help="Archive flag; declarations are archived to preserve the governance record.")

    @api.depends('director_id', 'declaration_type')
    def _compute_name(self):
        for rec in self:
            label = dict(rec._fields['declaration_type'].selection).get(rec.declaration_type)
            rec.name = ' - '.join(filter(None, [rec.director_id.name, label]))
