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


class NhsRiskAssurance(models.Model):
    _name = 'nhs.risk.assurance'
    _description = 'Risk Assurance (Three Lines of Defence)'
    _order = 'risk_id, line, sequence'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade',
                              help='The risk register entry this assurance is linked to.')
    sequence = fields.Integer(default=10,
                              help='Display order of this assurance within the risk record.')
    name = fields.Char(string='Assurance Description', required=True,
                       help='Describe the assurance activity or mechanism providing confidence that '
                            'controls are effective (e.g. "Monthly audit of medication reconciliation records").')
    line = fields.Selection([
        ('first', '1st Line — Management'),
        ('second', '2nd Line — Oversight / Compliance'),
        ('third', '3rd Line — Internal Audit'),
    ], string='Assurance Line', required=True, default='first',
       help='The Three Lines of Defence model line: '
            '1st Line = operational management controls; '
            '2nd Line = oversight, compliance, and risk functions; '
            '3rd Line = independent internal or external audit.')
    assurance_gap = fields.Boolean(string='Gap in Assurance',
                                   help='Tick if this assurance mechanism is absent, insufficient, or not functioning. '
                                        'An assurance gap weakens the evidence base that controls are effective.')
    source = fields.Char(string='Source', help='e.g. Audit ref, committee name')
