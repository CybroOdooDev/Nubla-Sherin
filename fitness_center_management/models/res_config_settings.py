# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Feature Toggles
    is_nutrition = fields.Boolean(
        string='Nutrition',
        config_parameter='fitness.is_nutrition',
        help="Manage nutrition subscribers, services and plans"
    )
    is_feedback = fields.Boolean(
        string='Feedback',
        config_parameter='fitness.is_feedback',
        help="Manage customer feedback regarding fitness services and plan"
    )
    is_auto_attendance = fields.Boolean(
        string='Automatic Attendance',
        config_parameter='fitness.is_auto_attendance',
        help="Automatically check-in/out members on portal login/logout"
    )

    # Mail Templates
    welcome_mail_template_id = fields.Many2one(
        'mail.template',
        string='Welcome Mail Template',
        config_parameter='fitness.welcome_mail_template_id'
    )
    invoice_mail_template_id = fields.Many2one(
        'mail.template',
        string='Invoice Mail Template',
        config_parameter='fitness.invoice_mail_template_id'
    )

    # Alert Days
    membership_renewal_days = fields.Integer(
        string='Membership Renewal Days',
        config_parameter='fitness.membership_renewal_days',
        default=10
    )
    expiry_alert_days = fields.Integer(
        string='Expiry Alert Days',
        config_parameter='fitness.expiry_alert_days',
        default=10
    )
