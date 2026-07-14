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


class NhsDsptStandard(models.Model):
    _name = 'nhs.dspt.standard'
    _description = 'DSPT Standard / Theme within an edition'
    _order = 'edition_id, sequence, name'

    name = fields.Char(
        string='Standard',
        required=True,
        help="Standard/theme name (National Data Guardian theme)."
    )
    edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Edition',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning edition."
    )
    code = fields.Char(
        string='Reference',
        help="Standard reference."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    assertion_def_ids = fields.One2many(
        'nhs.dspt.assertion.def',
        'standard_id',
        string='Assertions',
        help="Assertions under this standard."
    )
    assertion_count = fields.Integer(
        string='Assertion Count',
        compute='_compute_assertion_count',
    )

    @api.depends('assertion_def_ids')
    def _compute_assertion_count(self):
        for standard in self:
            standard.assertion_count = len(standard.assertion_def_ids)
