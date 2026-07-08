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


class NhsEstablishmentPost(models.Model):
    _inherit = 'nhs.establishment.post'

    training_requirement_profile_id = fields.Many2one(
        'nhs.requirement.profile',
        string='Training Requirement Profile',
        help="Every holder of this post inherits this profile's training requirements."
    )
    member_ids = fields.One2many(
        'nhs.workforce.member',
        'post_id',
        string='Workforce Members',
        help="Workforce members currently holding this post (training-compliance purposes)."
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
    )

    def _compute_member_count(self):
        for post in self:
            post.member_count = len(post.member_ids)

    def action_view_workforce_members(self):
        self.ensure_one()
        return {
            'name': 'Workforce Members',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'list,kanban,form',
            'domain': [('post_id', '=', self.id)],
            'context': {'default_post_id': self.id},
        }
