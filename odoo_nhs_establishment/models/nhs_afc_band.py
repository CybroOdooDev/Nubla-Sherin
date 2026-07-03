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


class NhsAfcBand(models.Model):
    _name = 'nhs.afc.band'
    _description = 'Agenda for Change Pay Band'
    _order = 'sequence, name'

    name = fields.Char(
        string='Band',
        required=True,
        help="Band name, e.g. 'Band 5'."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="1-9 ordering used for sorting and roll-up grouping."
    )
    pay_point = fields.Char(
        string='Pay Point',
        help="Optional spine / pay point within the band."
    )
    indicative_salary = fields.Monetary(
        string='Indicative Annual Salary',
        currency_field='currency_id',
        help="Editable indicative annual salary for this band/pay point. Agenda for Change"
             " pay is uplifted annually so this is reference data the customer maintains,"
             " never a hard-coded constant."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency for the indicative salary value."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Leave blank to make this band available to every company; set to scope it"
             " to a single organisation's pay scale."
    )
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_post_count',
        help="Number of funded posts currently on this band."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    def _compute_post_count(self):
        post_data = self.env['nhs.establishment.post']._read_group(
            [('band_id', 'in', self.ids)],
            ['band_id'], ['__count'],
        )
        counts = {band.id: count for band, count in post_data}
        for band in self:
            band.post_count = counts.get(band.id, 0)
