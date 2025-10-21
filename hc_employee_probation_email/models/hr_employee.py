# -*- coding: utf-8 -*-
#######################################################################################
#
#    Hai Cheung (China) Limited
#
#    Copyright (C) Hai Cheung (China) Limited.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################
from odoo import models
from datetime import date,timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _cron_send_onboarding_reminder(self):
        """Send onboarding reminder emails 30 days after onboarding date."""
        today = date.today()
        target_date = today - timedelta(days=30)
        employees = self.search([
            ('parent_id', '!=', False),
            ('onboard_date', '=', target_date),
        ])
        template = self.env.ref('hc_employee_probation_email.employee_probation_email_template',
                                raise_if_not_found=False)
        if template:
            for emp in employees:
                template.send_mail(emp.id, force_send=True)

