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


class NhsRiskRegister(models.Model):
    _name = 'nhs.risk.register'
    _description = 'Risk Register (tier)'
    _order = 'tier, name'

    name = fields.Char(string='Register Name', required=True,
                       help='A descriptive name for this register (e.g. "Pharmacy Department Risk Register" '
                            'or "Board Assurance Framework 2026/27").')
    tier = fields.Selection([
        ('local', 'Local / Departmental'),
        ('directorate', 'Directorate / Divisional'),
        ('corporate', 'Corporate Risk Register'),
        ('baf', 'Board Assurance Framework (BAF)'),
    ], string='Tier', required=True, default='local',
       help='The governance tier of this register. Local registers are department-level; '
            'Directorate registers span a division; Corporate registers are Trust-wide; '
            'the BAF is reported directly to the Board of Directors.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='The organisation this register belongs to.')
    owner_group_id = fields.Many2one('res.groups', string='Owner Group',
                                     help='The security group whose members own and maintain this register. '
                                          'Used for access control and notification routing.')
    description = fields.Text(string='Description',
                               help='Optional notes about the purpose, scope, or governance arrangements '
                                    'for this register.')
    active = fields.Boolean(default=True,
                            help='Untick to archive this register. Archived registers are hidden but risks '
                                 'linked to them are retained.')
    risk_count = fields.Integer(compute='_compute_risk_count',
                                help='Number of active risks currently held on this register.')

    def _compute_risk_count(self):
        RiskModel = self.env['nhs.risk']
        for reg in self:
            reg.risk_count = RiskModel.search_count([('register_id', '=', reg.id)])
