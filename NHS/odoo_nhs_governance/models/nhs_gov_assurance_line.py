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


class NhsGovAssuranceLine(models.Model):
    _name = 'nhs.gov.assurance.line'
    _description = 'Three Lines of Defence — Assurance Line'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True,
                       help="Display name (e.g. 'First Line — Operational Management').")
    code = fields.Selection([
        ('first', 'First Line (Operational Management)'),
        ('second', 'Second Line (Oversight Functions)'),
        ('third', 'Third Line (Independent Assurance)'),
    ], string='Code', required=True, index=True,
       help='The three-lines-of-defence category used to classify BAF assurances.')
    sequence = fields.Integer(string='Sequence', default=10, help='Display order among the lines of defence.')
    description = fields.Text(string='Description',
                              help='Guidance on what evidence belongs on this line of defence.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'An assurance line already exists for this code.',
    )
