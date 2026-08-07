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

class NHSComplianceBulkApplyWizard(models.TransientModel):
    """Wizard to bulk-apply compliance schedules for a selected discipline across multiple sites and buildings."""
    _name = 'nhs.compliance.bulk.apply.wizard'
    _description = 'Bulk Apply Discipline Schedule'

    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline', required=True,
                                    help='The statutory compliance discipline to bulk-apply schedules for.')
    compliance_type_ids = fields.Many2many('nhs.compliance.type', string='Compliance Types', required=True,
                                           help='The compliance types to schedule against the target locations.')
    site_ids = fields.Many2many('nhs.estate.site', string='Sites',
                                help='Filter the target locations by these specific NHS sites.')
    building_ids = fields.Many2many('nhs.estate.building', string='Buildings',
                                    help='Filter the target locations by these specific buildings.')
    start_date = fields.Date(string='Last Completed Date', default=fields.Date.today,
                             help='The baseline completion date to initialize compliance scheduling from.')

    @api.onchange('discipline_id')
    def _onchange_discipline_id(self):
        """Update compliance types domain and selection based on the chosen discipline."""
        if self.discipline_id:
            self.compliance_type_ids = self.discipline_id.type_ids.ids

    @api.onchange('site_ids')
    def _onchange_site_ids(self):
        """Clear building selections that do not belong to the currently selected sites.
        If one or more sites are selected, any previously chosen buildings that
        are not in those sites are removed.  When no site is selected the
        building list is left untouched so all buildings remain available.
        """
        if self.site_ids and self.building_ids:
            valid_buildings = self.building_ids.filtered(
                lambda b: b.site_id in self.site_ids
            )
            self.building_ids = valid_buildings

    def _get_items_to_create(self):
        """Return a list of dictionary values representing new compliance items to generate for
        the selected locations."""
        items = []
        locations = []
        if self.building_ids:
            for building in self.building_ids:
                locations.append((building.id, building.name, building.site_id.id))
        elif self.site_ids:
            buildings = self.env['nhs.estate.building'].search([('site_id', 'in', self.site_ids.ids)])
            for building in buildings:
                locations.append((building.id, building.name, building.site_id.id))
        else:
            buildings = self.env['nhs.estate.building'].search([])
            for building in buildings:
                locations.append((building.id, building.name, building.site_id.id))
        for building_id, building_name, site_id in locations:
            for comp_type in self.compliance_type_ids:
                existing = self.env['nhs.compliance.item'].search([
                    ('building_id', '=', building_id),
                    ('compliance_type_id', '=', comp_type.id),
                    ('active', '=', True)
                ])
                if existing:
                    continue
                items.append({
                    'name': f"{comp_type.name} - {building_name}",
                    'location_id': building_id,
                    'location_name': building_name,
                    'location': building_name,
                    'site_id': site_id,
                    'compliance_type_id': comp_type.id,
                    'discipline_id': self.discipline_id.id,
                })
        return items

    def action_apply(self):
        """Generate compliance items for the selected locations and navigate to their list view."""
        items = self._get_items_to_create()
        created_ids = []
        for item_data in items:
            comp_type = self.env['nhs.compliance.type'].browse(item_data['compliance_type_id'])
            vals = {
                'compliance_type_id': item_data['compliance_type_id'],
                'last_completed_date': self.start_date,
                'frequency_value': comp_type.default_frequency_value or 1,
                'frequency_unit': comp_type.default_frequency_unit or 'month',
                'lead_days': comp_type.default_lead_days or 14,
                'building_id': item_data['location_id'] or '',
                'site_id': item_data['site_id'] or '',
            }
            new_item = self.env['nhs.compliance.item'].create(vals)
            created_ids.append(new_item.id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bulk Apply Result',
            'res_model': 'nhs.compliance.item',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
            'target': 'current',
        }
