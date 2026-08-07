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


class NhsDsptOrgProfile(models.Model):
    """Represents an organisation-type profile (e.g., Trust, GP) used to filter DSPT requirements."""
    _name = 'nhs.dspt.org.profile'
    _description = 'DSPT Organisation-Type Profile'
    _order = 'sequence, name'

    name = fields.Char(
        string='Organisation Type',
        required=True,
        help="e.g. 'NHS Trust', 'GP Practice', 'Care Provider', 'Supplier / Partner'."
    )
    code = fields.Char(
        string='Code',
        help="Short reference code for this organisation type."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    description = fields.Text(
        string='Description',
        help="What kind of organisation this profile suits."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
