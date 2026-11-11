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

class NHSComplianceBulkApplyWizardLine(models.TransientModel):
    """Line model to preview compliance items that will be generated in bulk apply wizard."""
    _name = 'nhs.compliance.bulk.apply.wizard.line'
    _description = 'Bulk Apply Discipline Schedule Line'

    wizard_id = fields.Many2one('nhs.compliance.bulk.apply.wizard', string='Wizard', ondelete='cascade')
    selected = fields.Boolean(string='Select', default=True, help='Check to include this item in creation.')
    site_id = fields.Many2one('nhs.estate.site', string='Site')
    building_id = fields.Many2one('nhs.estate.building', string='Building')
    compliance_type_id = fields.Many2one('nhs.compliance.type', string='Compliance Type')
    item_name = fields.Char(string='Item Name Preview')
    start_date = fields.Date(string='Last Completed Date')
    next_due_date = fields.Date(string='Calculated Next Due Date')


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
    start_date = fields.Date(string='Last Completed Date',
                             help='The baseline completion date to initialize compliance scheduling from. '
                                  'Leave blank to start as due now.')
    line_ids = fields.One2many('nhs.compliance.bulk.apply.wizard.line', 'wizard_id',
                               string='Preview Items',
                               help='Preview of compliance items that will be generated.')

    @api.onchange('discipline_id')
    def _onchange_discipline_id(self):
        """Update compliance types domain and selection based on the chosen discipline."""
        if self.discipline_id:
            self.compliance_type_ids = self.discipline_id.type_ids.ids

    @api.onchange('site_ids')
    def _onchange_site_ids(self):
        """Clear building selections that do not belong to the currently selected sites."""
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
                locations.append({
                    'building_id': building.id,
                    'building_name': building.name,
                    'site_id': building.site_id.id,
                    'site_name': building.site_id.name,
                    'location_type': 'building'
                })
        elif self.site_ids:
            buildings = self.env['nhs.estate.building'].search([('site_id', 'in', self.site_ids.ids)])
            if buildings:
                for building in buildings:
                    locations.append({
                        'building_id': building.id,
                        'building_name': building.name,
                        'site_id': building.site_id.id,
                        'site_name': building.site_id.name,
                        'location_type': 'building'
                    })
            else:
                for site in self.site_ids:
                    locations.append({
                        'building_id': False,
                        'building_name': False,
                        'site_id': site.id,
                        'site_name': site.name,
                        'location_type': 'site'
                    })
        else:
            buildings = self.env['nhs.estate.building'].search([])
            if buildings:
                for building in buildings:
                    locations.append({
                        'building_id': building.id,
                        'building_name': building.name,
                        'site_id': building.site_id.id,
                        'site_name': building.site_id.name,
                        'location_type': 'building'
                    })
            else:
                sites = self.env['nhs.estate.site'].search([])
                for site in sites:
                    locations.append({
                        'building_id': False,
                        'building_name': False,
                        'site_id': site.id,
                        'site_name': site.name,
                        'location_type': 'site'
                    })
        for loc in locations:
            for comp_type in self.compliance_type_ids:
                search_domain = [
                    ('compliance_type_id', '=', comp_type.id),
                    ('active', '=', True)
                ]
                if loc['location_type'] == 'building':
                    search_domain.append(('building_id', '=', loc['building_id']))
                    location_name = loc['building_name']
                else:
                    search_domain.append(('building_id', '=', False))
                    search_domain.append(('site_id', '=', loc['site_id']))
                    location_name = loc['site_name']
                existing = self.env['nhs.compliance.item'].search(search_domain, limit=1)
                if existing:
                    continue
                if self.start_date:
                    from datetime import timedelta
                    from dateutil.relativedelta import relativedelta
                    unit = comp_type.default_frequency_unit or 'month'
                    val = comp_type.default_frequency_value or 1
                    if unit == 'day':
                        delta = timedelta(days=val)
                    elif unit == 'week':
                        delta = timedelta(weeks=val)
                    elif unit == 'month':
                        delta = relativedelta(months=val)
                    elif unit == 'year':
                        delta = relativedelta(years=val)
                    else:
                        delta = relativedelta(months=1)
                    next_due = self.start_date + delta
                else:
                    next_due = fields.Date.today()
                item_data = {
                    'name': f"{comp_type.name} — {location_name}",
                    'building_id': loc['building_id'] if loc['location_type'] == 'building' else False,
                    'site_id': loc['site_id'],
                    'compliance_type_id': comp_type.id,
                    'discipline_id': self.discipline_id.id,
                    'location_type': loc['location_type'],
                    'start_date': self.start_date,
                    'next_due_date': next_due,
                }
                items.append(item_data)
        return items

    def action_preview(self):
        """Generate and display the preview of compliance items that will be created."""
        self.ensure_one()
        self.line_ids.unlink()
        items = self._get_items_to_create()
        lines_vals = []
        for item in items:
            lines_vals.append({
                'wizard_id': self.id,
                'selected': True,
                'site_id': item['site_id'],
                'building_id': item['building_id'],
                'compliance_type_id': item['compliance_type_id'],
                'item_name': item['name'],
                'start_date': item['start_date'],
                'next_due_date': item['next_due_date'],
            })
        if lines_vals:
            self.env['nhs.compliance.bulk.apply.wizard.line'].create(lines_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.compliance.bulk.apply.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        """Generate compliance items for the selected locations and navigate to their list view."""
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not self.line_ids:
            self.action_preview()
            selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Items Created',
                    'message': 'No compliance items were selected for creation, or all items already exist.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        created_ids = []
        for line in selected_lines:
            comp_type = line.compliance_type_id
            vals = {
                'name': line.item_name,
                'compliance_type_id': comp_type.id,
                'last_completed_date': line.start_date,
                'frequency_value': comp_type.default_frequency_value or 1,
                'frequency_unit': comp_type.default_frequency_unit or 'month',
                'lead_days': comp_type.default_lead_days or 14,
                'site_id': line.site_id.id,
                'discipline_id': self.discipline_id.id,
            }
            if line.building_id:
                vals['building_id'] = line.building_id.id
            else:
                vals['building_id'] = False
            if not line.start_date:
                vals['next_due_date'] = fields.Date.today()
            new_item = self.env['nhs.compliance.item'].create(vals)
            if not line.start_date:
                new_item.write({'next_due_date': fields.Date.today()})
            created_ids.append(new_item.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bulk Apply Result',
            'res_model': 'nhs.compliance.item',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
            'target': 'current',
        }
