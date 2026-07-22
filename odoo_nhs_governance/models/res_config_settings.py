# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhs_gov_tor_review_lead_days = fields.Integer(
        string='ToR Review Reminder Lead Days',
        config_parameter='odoo_nhs_governance.tor_review_lead_days',
        default=30,
        help="Number of days before a terms-of-reference review date to raise reminders.",
    )
    nhs_gov_doi_refresh_lead_days = fields.Integer(
        string='DoI Refresh Reminder Lead Days',
        config_parameter='odoo_nhs_governance.doi_refresh_lead_days',
        default=30,
        help="Number of days before annual declaration refresh is due to raise reminders.",
    )
    nhs_gov_action_due_lead_days = fields.Integer(
        string='Action Due Reminder Lead Days',
        config_parameter='odoo_nhs_governance.action_due_lead_days',
        default=7,
        help="Number of days before a governance action due date to raise reminders.",
    )
