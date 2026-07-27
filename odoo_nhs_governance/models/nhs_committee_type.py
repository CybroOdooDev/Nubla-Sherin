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


class NhsCommitteeType(models.Model):
    _name = 'nhs.committee.type'
    _description = 'Committee Type (board / committee / sub-committee / group / council of governors)'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True,
                       help="Display name (e.g. 'Standing Committee', 'Council of Governors').")
    code = fields.Selection([
        ('board', 'Board'),
        ('committee', 'Standing Committee'),
        ('sub_committee', 'Sub-Committee'),
        ('group', 'Group'),
        ('council_of_governors', 'Council of Governors'),
    ], string='Code', required=True, index=True,
       help='The structural role this type plays in the reporting hierarchy — drives '
            'default behaviour such as whether a quorum rule or council-of-governors '
            'specific menus apply.')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Display order in the dropdown.')
    description = fields.Text(string='Description',
                              help='Guidance shown to administrators when choosing this type.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'A committee type already exists for this code.',
    )
