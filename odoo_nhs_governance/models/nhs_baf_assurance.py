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


class NhsBafAssurance(models.Model):
    _name = 'nhs.baf.assurance'
    _description = 'BAF Assurance Line'
    _order = 'risk_id, line_of_defence_id, date desc'

    risk_id = fields.Many2one('nhs.baf.risk', string='Principal Risk', required=True,
                              ondelete='cascade', help='The principal risk this assurance evidences.')
    company_id = fields.Many2one(related='risk_id.company_id', string='Company', store=True)
    name = fields.Char(string='Assurance', required=True,
                       help="The assurance (e.g. 'Internal audit report on X', 'monthly performance data').")
    line_of_defence_id = fields.Many2one('nhs.gov.assurance.line', string='Line Of Defence', required=True,
                                         help="First (operational) / Second (oversight) / Third (independent).")
    line_of_defence_code = fields.Selection(related='line_of_defence_id.code', string='Line Code', store=True)
    source = fields.Char(string='Source', help='Where the assurance comes from.')
    rating = fields.Selection([
        ('positive', 'Positive'),
        ('partial', 'Partial'),
        ('negative', 'Negative'),
    ], string='Rating', help='Whether the assurance is positive, partial or negative.')
    date = fields.Date(string='Date', help='When the assurance was obtained/reported.')
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence',
                                      help='Supporting evidence documents.')
