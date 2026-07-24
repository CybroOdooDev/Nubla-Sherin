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


class NhsBafObjective(models.Model):
    _name = 'nhs.baf.objective'
    _description = 'BAF Strategic Objective'
    _inherit = ['mail.thread']
    _order = 'code, name'

    name = fields.Char(string='Strategic Objective', required=True, tracking=True,
                       help="Strategic objective statement (e.g. 'Deliver safe, high-quality care').")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company,
                                 help='Owning organisation.')
    code = fields.Char(string='Reference', help='Objective reference (e.g. "SO1").')
    lead_partner_id = fields.Many2one('res.partner', string='Executive Lead',
                                      domain="[('is_nhs_board_member', '=', True)]",
                                      help='Executive lead for this objective.')
    risk_ids = fields.One2many('nhs.baf.risk', 'objective_id', string='Principal Risks',
                               help='Principal risks to this objective.')
    risk_count = fields.Integer(string='Principal Risk Count', compute='_compute_risk_count')
    highest_current_score = fields.Integer(string='Highest Current Score', compute='_compute_risk_count',
                                           help='The highest current risk score among this objective\'s '
                                                'principal risks.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.depends('risk_ids', 'risk_ids.current_score')
    def _compute_risk_count(self):
        for rec in self:
            rec.risk_count = len(rec.risk_ids)
            rec.highest_current_score = max(rec.risk_ids.mapped('current_score') or [0])

    def action_view_risks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Principal Risks',
            'res_model': 'nhs.baf.risk',
            'view_mode': 'list,form',
            'domain': [('objective_id', '=', self.id)],
            'context': {'default_objective_id': self.id},
        }
