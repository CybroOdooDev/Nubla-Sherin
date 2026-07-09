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


class NhsProfileAssignPostsWizard(models.TransientModel):
    _name = 'nhs.profile.assign.posts.wizard'
    _description = 'Assign existing posts to a training requirement profile'

    profile_id = fields.Many2one(
        'nhs.requirement.profile',
        string='Requirement Profile',
        required=True,
    )
    post_ids = fields.Many2many(
        'nhs.establishment.post',
        string='Posts',
        domain="[('status', '=', 'active')]",
        help="Pick from existing active posts — this links them to the profile,"
             " it does not create new posts."
    )

    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        for wizard in self:
            if wizard.profile_id:
                wizard.post_ids = wizard.profile_id.post_ids

    def action_confirm(self):
        self.ensure_one()
        previous = self.profile_id.post_ids
        to_unassign = previous - self.post_ids
        to_unassign.write({'training_requirement_profile_id': False})
        self.post_ids.write({'training_requirement_profile_id': self.profile_id.id})
        return {'type': 'ir.actions.act_window_close'}
