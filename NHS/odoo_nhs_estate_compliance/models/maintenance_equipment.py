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

class MaintenanceEquipment(models.Model):
    """Extension of standard maintenance equipment model to link with statutory compliance items."""
    _inherit = 'maintenance.equipment'

    compliance_item_ids = fields.One2many('nhs.compliance.item', 'equipment_id',
                                          string='Compliance Items',
                                          help='Compliance items linked to this piece of equipment.')
    compliance_item_count = fields.Integer(string='Compliance Item Count', compute='_compute_compliance_item_count',
                                           help='Total number of compliance items associated with this equipment.')

    @api.depends('compliance_item_ids')
    def _compute_compliance_item_count(self):
        """Compute the total number of compliance items linked to each equipment record."""
        for equipment in self:
            equipment.compliance_item_count = len(equipment.compliance_item_ids)

    def action_view_compliance_item(self):
        """Open a list/form view of all compliance items associated with this equipment record."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compliance Items',
            'res_model': 'nhs.compliance.item',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id}
        }
