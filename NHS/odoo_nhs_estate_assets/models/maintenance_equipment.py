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
    _inherit = 'maintenance.equipment'

    nhs_device_id = fields.Many2one(
        'nhs.device',
        string='NHS Device',
        ondelete='set null',
        help='Link a maintenance.equipment record to its NHS device (optional). '
             'When set, this equipment is managed through the NHS device register '
             'and its maintenance schedules drive standard maintenance requests.'
    )
    is_nhs_device = fields.Boolean(
        string='Is NHS Device',
        compute='_compute_is_nhs_device',
        store=True,
        help='Flag equipment that is an NHS-managed device. '
             'Automatically set when linked to an NHS device.'
    )
    archived_by_device_id = fields.Many2one(
        'nhs.device',
        string='Archived with Device',
        copy=False,
        index=True,
        help='Tracks the device that triggered automated cascade archiving.'
    )

    @api.depends('nhs_device_id')
    def _compute_is_nhs_device(self):
        """
        Compute whether this equipment is an NHS device.
        True when linked to an NHS device.
        """
        for record in self:
            record.is_nhs_device = bool(record.nhs_device_id)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to sync with NHS device if linked.
        """
        records = super(MaintenanceEquipment, self).create(vals_list)
        for record in records:
            if record.nhs_device_id:
                if not record.name or record.name == 'New':
                    record.name = record.nhs_device_id.display_name
                if record.nhs_device_id.responsible_user_id and not record.owner_user_id:
                    record.owner_user_id = record.nhs_device_id.responsible_user_id.id
                if not record.category_id:
                    category = self.env['maintenance.equipment.category'].search([
                        ('name', '=', 'Medical Device')
                    ], limit=1)
                    if not category:
                        category = self.env['maintenance.equipment.category'].create({'name': 'Medical Device'})
                    record.category_id = category.id
                if not record.maintenance_team_id:
                    team = self.env['maintenance.team'].search([
                        ('name', '=', 'NHS Technician Team')
                    ], limit=1)
                    if not team:
                        team = self.env['maintenance.team'].create({'name': 'NHS Technician Team'})
                    record.maintenance_team_id = team.id
        return records

    def write(self, vals):
        """
        Override write to sync changes with NHS device.
        """
        result = super(MaintenanceEquipment, self).write(vals)
        for record in self:
            if 'nhs_device_id' in vals or 'name' in vals:
                if record.nhs_device_id and 'name' in vals:
                    pass
        return result

    def action_view_nhs_device(self):
        """
        Open the linked NHS device form.
        """
        self.ensure_one()
        if not self.nhs_device_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': 'NHS Device',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device',
            'view_mode': 'form',
            'res_id': self.nhs_device_id.id,
        }
