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


class NhsRegulator(models.Model):
    _name = 'nhs.regulator'
    _description = 'Professional Regulator Reference'
    _order = 'sequence, name'

    name = fields.Char(
        string='Regulator',
        required=True,
        help="Regulator name (e.g. 'Nursing & Midwifery Council')."
    )
    code = fields.Char(
        string='Code',
        help="Short code (NMC / GMC / HCPC / GPhC / GDC)."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    default_cycle_months = fields.Integer(
        string='Typical Cycle (Months)',
        help="Typical registration/revalidation cycle, informational only."
    )
    registration_count = fields.Integer(
        string='Registration Count',
        compute='_compute_registration_count',
        help="Number of professional registrations currently recorded against this regulator."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _name_uniq = models.Constraint(
        'UNIQUE(name)',
        'A regulator with this name already exists!'
    )

    def _compute_registration_count(self):
        reg_data = self.env['nhs.registration']._read_group(
            [('regulator_id', 'in', self.ids)],
            ['regulator_id'], ['__count'],
        )
        counts = {regulator.id: count for regulator, count in reg_data}
        for regulator in self:
            regulator.registration_count = counts.get(regulator.id, 0)
