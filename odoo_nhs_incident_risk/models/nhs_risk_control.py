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


class NhsRiskControl(models.Model):
    _name = 'nhs.risk.control'
    _description = 'Risk Control'
    _order = 'risk_id, sequence'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade',
                              help='The risk register entry this control is linked to.')
    sequence = fields.Integer(default=10,
                              help='Display order of this control within the risk record.')
    name = fields.Char(string='Control Description', required=True,
                       help='Describe the control measure in place to reduce the likelihood or impact of this risk '
                            '(e.g. "Double-check policy in place for high-risk medications").')
    control_gap = fields.Boolean(string='Gap in Control',
                                 help='Tick if this control is absent, ineffective, or not consistently applied. '
                                      'A gap in control increases the residual risk exposure.')
    owner_id = fields.Many2one('res.users', string='Control Owner',
                               help='The person responsible for maintaining and monitoring this control measure.')
