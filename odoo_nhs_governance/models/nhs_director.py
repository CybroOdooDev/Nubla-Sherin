# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsDirector(models.Model):
    _name = 'nhs.director'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Director or Officer'
    _order = 'name'

    name = fields.Char(required=True, tracking=True, help="Director or officer name.")
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning organisation for company-level security.",
    )
    role_title = fields.Char(
        string='Board Role',
        tracking=True,
        help="Board or officer role, for example Chief Executive or Non-Executive Director.",
    )
    is_executive = fields.Boolean(
        string='Executive Director',
        tracking=True,
        help="Tick for executive directors; leave unticked for non-executive or external roles.",
    )
    appointment_date = fields.Date(tracking=True, help="Date appointed to the director or officer role.")
    term_end = fields.Date(tracking=True, help="Current appointment or term end date.")
    fppr_status = fields.Selection([
        ('not_checked', 'Not Checked'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('concern', 'Concern'),
    ], default='not_checked', string='FPPR Status', tracking=True,
        help="Fit and Proper Person Requirement check status for this director.")
    fppr_check_date = fields.Date(string='FPPR Check Date', help="Date of the latest FPPR check.")
    user_id = fields.Many2one('res.users', help="Linked Odoo user for access and action ownership.")
    partner_id = fields.Many2one('res.partner', help="Linked contact record for correspondence.")
    declaration_ids = fields.One2many(
        'nhs.declaration',
        'director_id',
        help="Declarations of interest recorded for this director or officer.",
    )
    committee_membership_ids = fields.One2many(
        'nhs.committee.member',
        'director_id',
        help="Committees and boards this director or officer sits on.",
    )
    active = fields.Boolean(default=True, help="Archive flag for former directors or officers.")
