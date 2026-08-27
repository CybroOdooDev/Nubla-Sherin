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


class NhsRosterWeekday(models.Model):
    """Reference data: the seven days of the week, used on rotation-template
    lines, demand lines and a member's fixed working-day pattern. Owned
    locally by rostering (odoo_nhs_staff_bank has its own nhs.weekday, but
    that module is only a soft/runtime link, so it cannot be depended on)."""
    _name = 'nhs.roster.weekday'
    _description = 'Weekday (Rostering)'
    _order = 'sequence'

    name = fields.Char(string='Day', required=True, translate=True)
    index = fields.Integer(
        string='Index',
        required=True,
        help="ISO weekday index, 0 = Monday .. 6 = Sunday."
    )
    sequence = fields.Integer(string='Sequence', default=10)

    _index_uniq = models.Constraint(
        'UNIQUE(index)',
        'Each weekday index must be unique!'
    )
