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

import logging
from odoo import models ,_


_logger = logging.getLogger(__name__)


class HrPlanWizard(models.TransientModel):
    _inherit = 'hr.plan.wizard'

    def action_launch(self):
        """Override to send offboarding email when plan launched and last_day is set."""
        res = super(HrPlanWizard, self).action_launch()

        template = self.env.ref(
                        'hc_employee_offboarding_launch.employee_offboarding_email_template',raise_if_not_found=False
        )
        print(template)

        # Loop over all selected employees in the wizard
        for employee in self.employee_ids:
            # Ensure it’s an offboarding plan and date is defined
            if getattr(self.plan_id, 'category', False) == 'offboarding' and self.last_day and template:
                print("MAIL")
                try:
                    # Send as superuser to bypass record rule / multi-company errors
                    template.sudo().send_mail(employee.id, force_send=True)

                    # Show popup notification in UI
                    self.env.user.notify_info(
                        message=_("Offboarding email notification sent to %s") % employee.name
                    )

                    _logger.info("Offboarding email sent successfully to %s", employee.name)

                except Exception as e:
                    _logger.warning(
                        "❌ Failed to send offboarding email for %s: %s",
                        employee.name, e
                    )

        return res





