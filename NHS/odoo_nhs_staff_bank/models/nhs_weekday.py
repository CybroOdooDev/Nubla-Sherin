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


class NhsWeekday(models.Model):
    """The 7 fixed days of the week, as real records rather than 7 separate
    boolean fields — lets a multi-day selection (e.g. the Bulk-Create Shifts
    wizard's recurrence pattern) use a single Many2many field with a compact
    tag widget instead of a hand-laid-out row of checkboxes.

    `index` matches Python's `date.weekday()` (0=Monday ... 6=Sunday), so
    callers can match a computed date's weekday straight against it."""
    _name = 'nhs.weekday'
    _description = 'Day of the Week'
    _order = 'index'

    name = fields.Char(string='Day', required=True)
    index = fields.Integer(
        string='Index',
        required=True,
        help="0=Monday ... 6=Sunday, matching Python's date.weekday()."
    )

    _index_uniq = models.Constraint(
        'UNIQUE(index)',
        'Each weekday index must be unique.'
    )
