# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    complaint_public_form_enabled = fields.Boolean(
        string='Enable Public Complaint Submission Form',
        config_parameter='odoo_nhs_complaints.public_form_enabled',
        help='Allow patients, relatives and advocates to submit complaints online at /complaint/submit/<token>.',
    )
    complaint_public_form_token = fields.Char(
        string='Public Form Token',
        config_parameter='odoo_nhs_complaints.public_form_token',
        help='Security token appended to the public form URL. Generate a new token to invalidate the old URL.',
    )
    complaint_anonymise_after_years = fields.Integer(
        string='Anonymise Complainant Data After (Years)',
        config_parameter='odoo_nhs_complaints.anonymise_after_years',
        default=10,
        help='Years after closure before the monthly anonymisation cron processes closed complaints (0 = disabled).',
    )
    complaint_default_timescale_id = fields.Many2one(
        'nhs.complaint.timescale',
        string='Default Response Timescale',
        config_parameter='odoo_nhs_complaints.default_timescale_id',
        help='Default timescale preset applied when a new formal complaint is received.',
    )

    def action_generate_public_form_token(self):
        import secrets
        token = secrets.token_urlsafe(16)
        self.complaint_public_form_token = token
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_complaints.public_form_token', token)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_public_form(self):
        self.ensure_one()
        token = self.complaint_public_form_token
        if not token:
            import secrets
            token = secrets.token_urlsafe(16)
            self.complaint_public_form_token = token
            self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_complaints.public_form_token', token)
        url = f"/complaint/submit/{token}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

