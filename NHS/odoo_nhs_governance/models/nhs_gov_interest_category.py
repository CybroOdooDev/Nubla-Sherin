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


class NhsGovInterestCategory(models.Model):
    _name = 'nhs.gov.interest.category'
    _description = 'Declaration of Interest Category'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True,
                       help="Display name (e.g. 'Financial Interest', 'Loyalty / Non-Financial').")
    code = fields.Selection([
        ('financial', 'Financial'),
        ('non_financial_professional', 'Non-Financial Professional'),
        ('non_financial_personal', 'Non-Financial Personal'),
        ('loyalty', 'Loyalty'),
        ('indirect', 'Indirect'),
        ('nil', 'Nil Return'),
    ], string='Code', required=True, index=True,
       help='The NHS England Managing Conflicts of Interest guidance category this declaration falls under.')
    sequence = fields.Integer(string='Sequence', default=10, help='Controls the display order of categories.')
    description = fields.Text(string='Description',
                              help='Guidance on what belongs in this category, shown to members when declaring.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'An interest category already exists for this code.',
    )
