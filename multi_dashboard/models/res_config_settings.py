# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    multi_dashboard_gemini_api_key = fields.Char(
        string='Gemini API Key',
        config_parameter='multi_dashboard.gemini_api_key',
        help="API Key for Google Gemini to power Natural Language Chart Generation."
    )
