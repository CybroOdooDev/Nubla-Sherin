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

ONCALL_CATEGORIES = [
    ('a', 'Category A'),
    ('b', 'Category B'),
]


class NhsOncallSupplementRate(models.Model):
    """Configurable table of on-call availability supplement percentages by
    rota frequency ('1 in N') and category (A/B)."""
    _name = 'nhs.oncall.supplement.rate'
    _description = 'On-Call Supplement Rate'
    _order = 'frequency_n, category'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. '1 in 8, Category A'."
    )
    frequency_code = fields.Char(
        string='Frequency Code',
        required=True,
        help="Short code for the rota frequency, e.g. '1_in_8'."
    )
    frequency_n = fields.Integer(
        string='Frequency (1 in N)',
        required=True,
        help="The N in '1 in N' - how often the doctor is on the on-call rota."
    )
    category = fields.Selection(
        ONCALL_CATEGORIES,
        string='Category',
        required=True,
        help="On-call category per the national contract."
    )
    supplement_pct = fields.Float(
        string='Availability Supplement (%)',
        required=True,
        digits=(16, 2),
        help="Availability supplement percentage. Informational only - not fed"
             " into payroll by this module."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help="Leave blank to make this rate available to every company."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    @api.depends('frequency_n', 'category')
    def _compute_name(self):
        """Build the display name from frequency and category, falling back
        to a plain placeholder until both are set rather than showing a
        literal '1 in ?, ?'."""
        for rate in self:
            category_label = dict(ONCALL_CATEGORIES).get(rate.category)
            if rate.frequency_n and category_label:
                rate.name = '1 in %s, %s' % (rate.frequency_n, category_label)
            else:
                rate.name = 'New On-Call Supplement Rate'
