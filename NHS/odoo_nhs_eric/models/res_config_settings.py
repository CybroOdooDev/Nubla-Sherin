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
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eric_validation_policy = fields.Selection(
        selection=[
            ('warn', 'Warn Only'),
            ('block', 'Block Finalisation')
        ],
        string='Validation Policy',
        default='block',
        config_parameter='odoo_nhs_eric.eric_validation_policy',
        help='Determines whether validation errors block finalisation (Block) '
             'or just show warnings (Warn).'
    )
    eric_auto_populate_on_create = fields.Boolean(
        string='Auto-Populate on Create',
        config_parameter='odoo_nhs_eric.eric_auto_populate_on_create',
        help='Whether to automatically run the populate action when a new '
             'return is created.'
    )
    eric_carry_forward_manual = fields.Boolean(
        string='Auto-Carry Forward Manual Items',
        config_parameter='odoo_nhs_eric.eric_carry_forward_manual',
        help='Whether to automatically carry forward manual items from the '
             'prior year when creating a new return.'
    )
    anomaly_threshold_pct = fields.Float(
        string='Anomaly Threshold Percent',
        default=50.0,
        config_parameter='odoo_nhs_eric.anomaly_threshold_pct',
        help="Percentage threshold above which a value is flagged as anomalous (0-100)."
    )

