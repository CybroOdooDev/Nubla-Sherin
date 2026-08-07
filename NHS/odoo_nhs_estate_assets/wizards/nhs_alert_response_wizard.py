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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models
from odoo.exceptions import UserError

class NHSAlertResponseWizard(models.TransientModel):
    """
    Alert Response Report Wizard
    ============================
    Allows users to filter safety alerts by multi-selected categories and statuses,
    and generate a downloadable PDF report.
    """
    _name = 'nhs.alert.response.wizard'
    _description = 'Alert Response Report Wizard'

    category_ids = fields.Many2many(
        'nhs.device.category',
        string='Device Categories',
        help='Select one or more device categories to filter alerts (leave empty for all categories).'
    )
    state = fields.Selection(
        selection=[
            ('all', 'All States'),
            ('open', 'Open'),
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
        ],
        string='Alert State',
        default='all',
        required=True,
        help='Select alert state to filter (or All States).'
    )

    def action_generate_pdf(self):
        """
        Generate and download the Alert Response PDF report matching selected criteria.
        """
        self.ensure_one()
        domain = []
        if self.category_ids:
            domain.extend([
                '|',
                ('affected_category_id', 'in', self.category_ids.ids),
                ('line_ids.device_id.category_id', 'in', self.category_ids.ids)
            ])
        if self.state and self.state != 'all':
            domain.append(('state', '=', self.state))
        alerts = self.env['nhs.device.alert'].search(domain)
        if not alerts:
            raise UserError('No safety alerts found matching the selected criteria.')
        return self.env.ref('odoo_nhs_estate_assets.action_report_nhs_alert_response').report_action(alerts)
