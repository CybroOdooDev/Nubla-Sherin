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


class NhsShiftType(models.Model):
    """Reference data for the kind of shift being covered — day, night,
    weekend, bank holiday — which drives which rate card line applies."""
    _name = 'nhs.shift.type'
    _description = 'Bank Shift Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Shift Type',
        required=True,
        translate=True,
        help="Shift type, e.g. 'Day', 'Night', 'Weekend', 'Bank Holiday'."
    )
    code = fields.Char(
        string='Code',
        help="Short code for the shift type, used in exports."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    is_unsocial = fields.Boolean(
        string='Unsocial Hours',
        help="Marks this shift type as attracting an unsocial-hours enhancement"
             " by default (night/weekend/bank holiday, typically)."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Leave blank to make this shift type available to every company."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _name_uniq = models.Constraint(
        'UNIQUE(name, company_id)',
        'A shift type with this name already exists for this company!'
    )
