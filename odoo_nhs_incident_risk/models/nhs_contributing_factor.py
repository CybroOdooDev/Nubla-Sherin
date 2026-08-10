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


class NhsContributingFactor(models.Model):
    _name = 'nhs.contributing.factor'
    _description = 'Contributing Factor (Yorkshire Contributory Factors Framework)'
    _order = 'group_name, name'

    group_name = fields.Selection([
        ('patient', 'Patient Factors'),
        ('task', 'Task & Technology'),
        ('individual', 'Individual Staff'),
        ('team', 'Team Factors'),
        ('environment', 'Work Environment'),
        ('organisational', 'Organisational & Management'),
        ('external', 'External Factors'),
    ], string='Group', required=True,
       help='The Yorkshire Contributory Factors Framework group this factor belongs to. '
            'Groups cover the main system domains that can contribute to patient safety incidents.')
    name = fields.Char(string='Factor', required=True,
                       help='The specific contributing factor within its group '
                            '(e.g. "Distraction", "Inadequate staffing levels", "Equipment failure").')
    active = fields.Boolean(default=True,
                            help='Untick to retire this factor. Retired factors are hidden from '
                                 'investigation forms but remain on historical investigation records.')
