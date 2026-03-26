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
import json
import base64
from odoo import fields, models, _
from odoo.exceptions import UserError


class ImportChart(models.TransientModel):
    """"Wizard to import dashboard charts from a JSON file."""
    _name = 'import.chart'
    _description = 'Import Chart from JSON'

    dashboard_id = fields.Many2one(
        'multi.dashboards',
        'Target Dashboard',
        required=True
    )
    json_file = fields.Binary(string='JSON File', required=True)
    file_name = fields.Char('File Name')

    def action_import_chart(self):
        """ Import charts from the uploaded JSON file and create records on the dashboard.charts model. """
        self.ensure_one()
        try:
            # Decode the base64 file
            file_content = base64.b64decode(self.json_file).decode('utf-8')
            config_list = json.loads(file_content)

            # Ensure we handle both single objects and lists
            if isinstance(config_list, dict):
                config_list = [config_list]

            created_count = 0
            for config in config_list:
                vals = {
                    'name': config.get('name', 'Imported Chart'),
                    'dashboard_id': self.dashboard_id.id,
                    'chart_type': config.get('chart_type'),
                    'model_id': config.get('model_id'),
                    'filter': config.get('filter', '[]'),
                    'measure_aggregation': config.get('measure_aggregation'),
                    'measure_field_id': config.get('measure_field_id'),
                    'widget_color': config.get('widget_color'),
                    'layout_style': config.get('layout_style'),
                    'tile_font_style': config.get('tile_font_style'),
                    'font_color': config.get('font_color'),
                    'todo_color': config.get('todo_color', 4),
                    'list_group_field_id': config.get('list_group_field_id'),
                    'list_sort_field_id': config.get('list_sort_field_id'),
                    'list_sort_direction': config.get('list_sort_direction',
                                                      'desc'),
                    'list_limit': config.get('list_limit', 10),
                    'limit_per_page': config.get('limit_per_page', 10),
                    'list_row_clickable': config.get('list_row_clickable',
                                                     True),
                    'chart_group_field_id': config.get('chart_group_field_id'),
                    'chart_sub_group_field_id': config.get(
                        'chart_sub_group_field_id'),
                    'chart_orientation': config.get('chart_orientation',
                                                    'vertical'),
                    'progress_target_static': config.get('progress_target_static', 0),
                    'chart_date_group_by': config.get('chart_date_group_by'),
                    'enable_forecast': config.get('enable_forecast', False),
                    'forecast_periods': config.get('forecast_periods', 3),
                    'forecast_method': config.get('forecast_method', 'trend'),
                    'forecast_ai_cache_ttl_hours': config.get('forecast_ai_cache_ttl_hours', 24),
                    'forecast_history_periods': config.get('forecast_history_periods', 24),

                    'gs_x': config.get('gs_x', 0),
                    'gs_y': config.get('gs_y', 0),
                    'gs_w': config.get('gs_w', 4),
                    'gs_h': config.get('gs_h', 4),
                }

                if config.get('todo_ids'):
                    vals['todo_ids'] = [
                        fields.Command.create({
                            'name': todo.get('name'),
                            'sequence': todo.get('sequence', 10),
                            'is_done': todo.get('is_done', False),
                        }) for todo in config.get('todo_ids')
                    ]

                if config.get('list_field_ids'):
                    vals['list_field_ids'] = [
                        fields.Command.create({
                            'field_id': field.get('field_id'),
                            'sequence': field.get('sequence', 10),
                        }) for field in config.get('list_field_ids')
                    ]

                if config.get('chart_measure_field_ids'):
                    vals['chart_measure_field_ids'] = config.get(
                        'chart_measure_field_ids')

                if config.get('chart_measure_field_ids'):
                    vals['chart_measure_field_ids'] = [
                        fields.Command.set(
                            config.get('chart_measure_field_ids'))
                    ]
                # Create the record
                self.env['multi.dashboard.charts'].create(vals)
                created_count += 1

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Successful'),
                    'message': _(
                        'Successfully imported %s chart(s).') % created_count,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_("Failed to import JSON: %s") % str(e))
