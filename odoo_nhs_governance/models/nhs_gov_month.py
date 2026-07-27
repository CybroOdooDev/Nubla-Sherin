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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class NhsGovMonth(models.Model):
    _name = 'nhs.gov.month'
    _description = 'Calendar Month (cycle-of-business scheduling)'
    _order = 'code'

    name = fields.Char(string='Name', required=True, translate=True,
                       help="e.g. 'January'.")
    code = fields.Integer(string='Month Number', required=True,
                         help='Calendar month number, 1 (January) to 12 (December).')

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'A month record already exists for this month number.',
    )
