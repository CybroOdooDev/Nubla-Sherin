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

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    due_soon_window = fields.Integer(
        string='Due Soon Window (Days)',
        default=30,
        config_parameter='odoo_nhs_estate_assets.due_soon_window',
        help='Number of days before a maintenance/calibration due date '
             'when the status changes to "Due Soon".'
    )
    overdue_escalation_days = fields.Integer(
        string='Overdue Escalation Threshold (Days)',
        default=7,
        config_parameter='odoo_nhs_estate_assets.overdue_escalation_days',
        help='Number of days past due before triggering escalation activities to EBME Managers.'
    )
    expiry_reminder_window = fields.Integer(
        string='Expiry Reminder Window (Days)',
        default=90,
        config_parameter='odoo_nhs_estate_assets.expiry_reminder_window',
        help='Number of days before warranty/service contract expiry '
             'when the "Expiring" flag is triggered.'
    )
    indicative_depreciation_method = fields.Selection(
        selection=[
            ('straight_line', 'Straight-Line Depreciation'),
            ('none', 'No Depreciation (Cost Only)'),
        ],
        string='Indicative Value Method',
        default='straight_line',
        config_parameter='odoo_nhs_estate_assets.indicative_depreciation_method',
        help='Method used for non-accounting indicative value calculations across the estate.'
    )