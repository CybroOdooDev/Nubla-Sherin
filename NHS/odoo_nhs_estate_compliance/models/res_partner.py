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
from odoo import fields, models,api

class ResPartner(models.Model):
    """Extension of standard partner model to link with NHS assignment roles."""
    _inherit = 'res.partner'

    assignment_roles_ids = fields.One2many('nhs.duty.assignment', 'person_id',
                                          string='Assignment Roles',
                                          help='Assignment roles linked to this piece of partner.')
    assignment_roles_count = fields.Integer(string='Assignment Roles Count', compute='_compute_assignment_roles_count',
                                           help='Total number of assignment roles associated with this partner.')

    @api.depends('assignment_roles_ids')
    def _compute_assignment_roles_count(self):
        """Compute the total number of assignment roles linked to each partner record."""
        for person in self:
            person.assignment_roles_count = len(person.assignment_roles_ids)

    def action_view_assignment_roles(self):
        """Open a list/form view of all assignment roles associated with this partner record."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assignment Roles',
            'res_model': 'nhs.duty.assignment',
            'view_mode': 'list,form',
            'domain': [('person_id', '=', self.id)],
            'context': {'default_person_id': self.id}
        }