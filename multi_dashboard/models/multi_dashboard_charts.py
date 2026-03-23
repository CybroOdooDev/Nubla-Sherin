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
import logging
import pytz
from google import genai
from google.genai import types
from itertools import groupby
from operator import itemgetter
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import date_utils
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


def _tz_get(self):
    return _tzs


class MultiDashboardCharts(models.Model):
    """ Model representing individual charts/widgets on the multi-dashboard."""
    _name = 'multi.dashboard.charts'
    _description = 'Multi Dashboard Charts'
    _order = 'id desc'

    name = fields.Char('Name', required=True,
                       help='Name of the chart/widget')
    dashboard_id = fields.Many2one('multi.dashboards',
                                   'Dashboard',
                                   required=True,
                                   ondelete='cascade',
                                   help='Parent dashboard for this chart/widget')
    chart_type = fields.Selection([('clock', 'Clock'),
                                   ('tile', 'Tile'),
                                   ('todo', 'ToDo'),
                                   ('list', 'List View'),
                                   ('bar', 'Bar Chart'),
                                   ('line', 'Line Chart'),
                                   ('pie', 'Pie Chart'),
                                   ('donut', 'Donut Chart'),
                                   ('funnel', 'Funnel Chart'),
                                   ('pyramid', 'Pyramid Chart'),
                                   ('radar', 'Radar Chart'),
                                   ('stacked', 'Stacked Column Chart'),
                                   ('scatter', 'Scatter Chart'),
                                   ('radialBar', 'Radial Bar Chart'),
                                   ('progress', 'Progress Bar'),
                                   ],
                                  'Chart Type',
                                  required=True, default='tile',
                                  help='Type of the chart/widget')
    am_chart_theme = fields.Selection([
        ('default', 'Default'),
        ('material', 'Material'),
        ('kelly', 'Kelly'),
        ('dataviz', 'Data Viz'),
        ('moonrise', 'Moonrise'),
        ('frozen', 'Frozen'),
        ('spiritedaway', 'Spirited Away'),
    ],
        'Chart Theme',
        default='default',
        required=True,
        help="Select the color theme for the AmCharts.")
    model_id = fields.Many2one('ir.model',
                               'Model',
                               domain=[('transient', '=', False)],
                               help='Select the model for the chart data source')
    model_name = fields.Char("Model Name",
                             related='model_id.model',
                             help="Added model_id model")
    measure_aggregation = fields.Selection([('sum', 'Sum'),
                                            ('count', 'Count'),
                                            ('avg', 'Average')],
                                           'Measure Aggregation',
                                           default='sum',
                                           help='Aggregation method for the measure field')
    measure_field_id = fields.Many2one('ir.model.fields',
                                       'Measure Field',
                                       domain="[('model_id', '=', model_id), "
                                              "('ttype', 'in', ('integer', 'float', 'monetary'))]",
                                       help='Field to be used as measure in the chart')
    filter = fields.Char('Filter',
                         help='Filter the records for the chart data source')
    filter_date_field_id = fields.Many2one('ir.model.fields',
                                          'Filter Date Field',
                                          domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]",
                                          help='Select the date field to be used for global dashboard filtering')

    # List View specific fields
    list_field_ids = fields.One2many('multi.dashboard.list',
                                     'chart_id',
                                     'Fields to Display',
                                     help='Select fields to display in the list view')
    list_limit = fields.Integer('Record Limit',
                                default=10,
                                help='Maximum number of records to display in list view')
    limit_per_page = fields.Integer('Records per Page',
                                    default=10,
                                    help='Number of records to show per page in list view')
    list_row_clickable = fields.Boolean('Clickable Rows',
                                        default=True,
                                        help='Allow clicking rows to open records')
    list_sort_field_id = fields.Many2one('ir.model.fields',
                                         'Sort By Field',
                                         domain="[('id', 'in', available_sort_fields_ids)]",
                                         help="Select the field to sort the records by")
    available_sort_fields_ids = fields.Many2many('ir.model.fields',
                                                 string='Available Sort Fields',
                                                 compute='_compute_available_sort_fields',
                                                 help='Fields available for sorting the list view')
    list_sort_direction = fields.Selection([('asc', 'Ascending'),
                                            ('desc', 'Descending')],
                                           'Sort Direction',
                                           default='desc',
                                           help='Direction to sort the records in list view')
    list_group_field_id = fields.Many2one('ir.model.fields',
                                          'Group By',
                                          domain="[('model_id', '=', model_id), ('ttype', 'in', ['many2one', 'selection', 'char', 'date'])]",
                                          help="Select a field to group the records by")

    # To-Do specific fields
    todo_ids = fields.One2many('multi.dashboard.todo',
                               'chart_id',
                               'ToDo Items',
                               help="List of ToDo items for the ToDo widget")
    todo_color = fields.Integer('Color',
                                default=4,
                                help='Color for widgets')

    # Chart Configuration (Bar, Line, Pie, Donut)
    chart_measure_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Measure Field (Y-axis)',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('integer', 'float', 'monetary'))]",
        help="The numeric field to aggregate (e.g., Total, Quantity)."
    )
    chart_group_field_id = fields.Many2one(
        'ir.model.fields',
        'Group By (X-axis)',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('many2one', 'selection', 'char', 'date', 'datetime'))]",
        help="The field to categorize data by (e.g., Salesperson, Status, Date)."
    )
    chart_group_field_id_type = fields.Selection(
        string="Group Field Type",
        related='chart_group_field_id.ttype',
        readonly=True,
        help='Technical type of the Group By field, used for dynamic grouping options.'
    )
    # Specific support for Date/Datetime grouping
    chart_date_group_by = fields.Selection(
        [('day', 'Day'),
         ('week', 'Week'),
         ('month', 'Month'),
         ('quarter', 'Quarter'),
         ('year', 'Year')],
        'Date Granularity',
        default='month',
        help="If the 'Group By' field is a date, how should it be grouped?"
    )
    chart_sub_group_field_id = fields.Many2one(
        'ir.model.fields',
        'Sub-Group By',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('many2one', 'selection', 'char'))]",
        help="Optional second level of grouping (e.g., Status within Salesperson)."
    )
    chart_orientation = fields.Selection([('vertical', 'Vertical'),
                                          ('horizontal', 'Horizontal')],
                                         'Orientation',
                                         default='vertical',
                                         help='Orientation of the chart.')

    # Layout configuration
    widget_color = fields.Char('Widget Color',
                               help='Background color or gradient for the tile widget.')
    layout_style = fields.Char("Layout Style",
                               help="CSS class for layout style (e.g., centered, side, corner)")
    tile_font_style = fields.Char('Font Style',
                                  help='CSS class for font style in tile widget')
    font_color = fields.Char('Font Color',
                             default="#000000",
                             help='Font color for the tile widget')
    tile_icon = fields.Char('Tile Icon', help='FontAwesome class for the tile icon (e.g. fa-users)')
    tile_unit_format = fields.Selection([
        ('auto', 'Auto'),
        ('none', 'None'),
        ('k', 'Thousands (K)'),
        ('l', 'Lakhs (L)'),
        ('m', 'Millions (M)'),
        ('c', 'Crores (C)'),
    ], string='Unit Format', default='auto', help='Display values using selected unit.')

    # KPI Configuration
    is_kpi = fields.Boolean('Show KPI', help='Display a KPI indicator on the tile')
    kpi_comparison = fields.Selection([
        ('previous_period', 'Previous Period'),
        ('previous_year', 'Same Period Last Year'),
        ('target', 'Target Value'),
    ], string='Comparison', default='previous_period', help='Compare current data with another period or a target goal')

    clock_format = fields.Selection([('12', '12 Hr'), ('24', '24 Hr')],
                                    'Format',
                                    default='24', help='Mention format')
    tz = fields.Selection(_tzs, string='Timezone',
                          default=lambda self: self.env.user.tz,
                          help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                               "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                               "Anywhere else, time values are computed according to the time offset of your web client.")

    # Progress Bar Configuration
    progress_target_static = fields.Float("Target Value",
                                          help="Manual target goal")
    # Position configuration
    gs_x = fields.Integer('Position X', default=0,
                          help='Horizontal position of the widget on the dashboard grid')
    gs_y = fields.Integer('Position Y', default=0,
                          help='Vertical position of the widget on the dashboard grid')
    gs_w = fields.Integer('Width', default=3,
                          help='Width of the widget in grid units')
    gs_h = fields.Integer('Height', default=3,
                          help='Height of the widget in grid units')

    widget_preview = fields.Char('Preview',
                                 help='Preview of the widget configuration.')
    use_background_gradient = fields.Boolean('Use Background Gradient', default=False,
                                             help='Apply a linear gradient background to the widget.')

    @api.depends('model_id', 'list_field_ids')
    def _compute_available_sort_fields(self):
        """Compute available fields for sorting based on selected model"""
        # i dont need to have the computed fields
        for record in self:
            # Filter out computed fields
            if record.model_id:
                non_computed_fields = record.list_field_ids.filtered(
                    lambda f: not f.field_id.compute
                ).mapped('field_id')
                record.available_sort_fields_ids = non_computed_fields
            else:
                record.available_sort_fields_ids = False

    @api.onchange('chart_type')
    def _onchange_chart_type(self):
        """Set default dimensions based on chart type"""
        if self.chart_type in ['tile', 'todo']:
            self.gs_w = 3
            self.gs_h = 4
        elif self.chart_type == 'clock':
            self.gs_w = 3
            self.gs_h = 3
        elif self.chart_type == 'progress':
            self.gs_w = 4
            self.gs_h = 2
        elif self.chart_type == 'insight':
            self.gs_w = 4
            self.gs_h = 3
        else:
            self.gs_w = 6
            self.gs_h = 6

    def get_widget_value(self, date_filter=None):
        """Compute data for the widget based on configuration"""
        self.ensure_one()

        try:
            date_domain = self._get_date_domain(date_filter)

            if self.chart_type == 'clock':
                return {
                    'id': self.id,
                    'name': self.name,
                    'chart_type': 'clock',
                    'todo_color': self.todo_color,
                    'tz': self.tz,
                    'clock_format': self.clock_format,
                    'use_background_gradient': self.use_background_gradient,
                }
            elif self.chart_type == 'tile':
                domain = safe_eval(self.filter) if self.filter else []
                if date_domain:
                    domain += date_domain
                model = self.env[self.model_name]

                field_name = self.measure_field_id.name if self.measure_field_id else None

                records = model.search(domain)
                if self.measure_aggregation == 'count':
                    value = len(records)
                elif self.measure_aggregation in ['sum', 'avg']:
                    if not field_name:
                        return {'value': 0,
                                'error': "No measure field configured"}
                    values = records.mapped(field_name)
                    if self.measure_aggregation == 'sum':
                        value = sum(values) if values else 0
                    else:
                        value = sum(values) / len(values) if values else 0
                else:
                    value = 0

                layout_map = {
                    'layout_1': 'tile-layout-center',
                    'layout_2': 'tile-layout-side',
                    'layout_3': 'tile-layout-corner'
                }

                # Apply unit formatting
                display_value = round(value, 2)
                unit_format = self.tile_unit_format or 'auto'

                if unit_format == 'auto':
                    if value >= 10000000: # Crores
                        display_value = f"{round(value / 10000000, 1)}C"
                    elif value >= 1000000: # Millions
                        display_value = f"{round(value / 1000000, 1)}M"
                    elif value >= 100000: # Lakhs
                        display_value = f"{round(value / 100000, 1)}L"
                    elif value >= 1000: # Thousands
                        display_value = f"{round(value / 1000, 1)}K"
                elif unit_format == 'k':
                    display_value = f"{round(value / 1000, 1)}K"
                elif unit_format == 'l':
                    display_value = f"{round(value / 100000, 1)}L"
                elif unit_format == 'm':
                    display_value = f"{round(value / 1000000, 1)}M"
                elif unit_format == 'c':
                    display_value = f"{round(value / 10000000, 1)}C"

                kpi_data = False
                if self.is_kpi:
                    if self.kpi_comparison == 'target':
                        target_val = self.progress_target_static or 1.0
                        percentage = (value / target_val * 100) if target_val > 0 else 0
                        kpi_data = {
                            'percentage': round(percentage, 1),
                            'direction': 'up' if percentage >= 100 else 'down',
                            'comparison_label': 'of Target'
                        }
                    elif date_filter:
                        prev_domain = self._get_previous_period_domain(date_filter)
                        if prev_domain:
                            full_prev_domain = safe_eval(self.filter) if self.filter else []
                            full_prev_domain += prev_domain
                            prev_records = model.search(full_prev_domain)
                            
                            if self.measure_aggregation == 'count':
                                prev_value = len(prev_records)
                            elif self.measure_aggregation in ['sum', 'avg']:
                                prev_values = prev_records.mapped(field_name)
                                if self.measure_aggregation == 'sum':
                                    prev_value = sum(prev_values) if prev_values else 0
                                else:
                                    prev_value = sum(prev_values) / len(prev_values) if prev_values else 0
                            else:
                                prev_value = 0

                            if prev_value > 0:
                                percentage = ((value - prev_value) / prev_value) * 100
                            elif value > 0:
                                percentage = 100
                            else:
                                percentage = 0
                            
                            kpi_data = {
                                'percentage': round(abs(percentage), 1),
                                'direction': 'up' if percentage >= 0 else 'down',
                                'comparison_label': 'vs Prev. Period' if self.kpi_comparison == 'previous_period' else 'vs Last Year'
                            }

                return {
                    'id': self.id,
                    'name': self.name,
                    'value': display_value,
                    'widget_color': self.widget_color or 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'layout_style': layout_map.get(self.layout_style, 'tile-layout-center'),
                    'tile_font_style': self.tile_font_style or 'tile-style-modern',
                    'font_color': self.font_color or '#ffffff',
                    'tile_icon': self.tile_icon,
                    'kpi_data': kpi_data,
                    'use_background_gradient': self.use_background_gradient,
                }

            elif self.chart_type == 'todo':
                vals = {
                    'id': self.id,
                    'name': self.name,
                    'todo_color': self.todo_color,
                    'chart_type': self.chart_type,
                    'use_background_gradient': self.use_background_gradient,
                    'todos': [{
                        'id': t.id,
                        'name': t.name,
                        'is_done': t.is_done
                    } for t in self.todo_ids]
                }
                return vals
            elif self.chart_type == 'progress':
                domain = safe_eval(self.filter) if self.filter else []
                if date_domain:
                    domain += date_domain
                model = self.env[self.model_name]

                # Calculate Current Value (reuse your tile logic)
                records = model.search(domain)
                field_name = self.measure_field_id.name

                if self.measure_aggregation == 'count':
                    current_val = len(records)
                else:
                    values = records.mapped(field_name)
                    current_val = sum(values) if values else 0
                    if self.measure_aggregation == 'avg' and len(records) > 0:
                        current_val = current_val / len(records)

                # Calculate Target Value
                target_val = self.progress_target_static

                # Calculate Percentage
                percentage = (current_val / target_val * 100) if target_val > 0 else 0

                return {
                    'id': self.id,
                    'name': self.name,
                    'current_value': round(current_val, 2),
                    'target_value': round(target_val, 2),
                    'percentage': min(round(percentage, 2), 100),
                    'chart_type': 'progress',
                    'todo_color': self.todo_color,
                    'use_background_gradient': self.use_background_gradient,
                }
            elif self.chart_type == 'list':
                return self._get_list_view_data(date_domain)
            else:
                return self._get_amcharts_data(date_domain)

        except Exception as e:
            return {'value': 0, 'error': str(e)}

    def _get_date_domain(self, date_filter=None):
        """Build the dashboard date domain for this widget."""
        self.ensure_one()

        date_domain = []
        if not date_filter or not isinstance(date_filter, dict):
            return date_domain

        start_date = date_filter.get('start_date')
        end_date = date_filter.get('end_date')
        if not start_date and not end_date:
            return date_domain

        date_field = self.filter_date_field_id
        if not date_field and self.model_id:
            fallback_names = ['date', 'date_order', 'invoice_date', 'create_date']
            for name in fallback_names:
                found = self.env['ir.model.fields'].search([
                    ('model_id', '=', self.model_id.id),
                    ('name', '=', name),
                    ('ttype', 'in', ('date', 'datetime'))
                ], limit=1)
                if found:
                    date_field = found
                    break

        if not date_field:
            _logger.warning(
                "Widget %s (%s) received date filter but has no Filter Date Field and no suitable fallback found.",
                self.id, self.name
            )
            return date_domain

        field_name = date_field.name
        if start_date:
            date_domain.append((field_name, '>=', start_date))
        if end_date:
            if date_field.ttype == 'datetime':
                date_domain.append((field_name, '<=', f"{end_date} 23:59:59"))
            else:
                date_domain.append((field_name, '<=', end_date))

        _logger.info(
            "Widget %s (%s) applying date filter on %s: %s -> %s",
            self.id, self.name, field_name, date_filter.get('label'), date_domain
        )
        return date_domain

    def _get_previous_period_domain(self, date_filter=None):
        """Calculate the domain for the previous period for KPI comparison."""
        self.ensure_one()
        if not date_filter or not isinstance(date_filter, dict):
            return []

        start_date_str = date_filter.get('start_date')
        end_date_str = date_filter.get('end_date')
        if not start_date_str or not end_date_str:
            return []

        try:
            start_date = fields.Date.from_string(start_date_str)
            end_date = fields.Date.from_string(end_date_str)
            
            if self.kpi_comparison == 'previous_period':
                duration = (end_date - start_date).days + 1
                prev_start = start_date - relativedelta(days=duration)
                prev_end = start_date - relativedelta(days=1)
            elif self.kpi_comparison == 'previous_year':
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
            else:
                return []

            date_field = self.filter_date_field_id
            if not date_field and self.model_id:
                fallback_names = ['date', 'date_order', 'invoice_date', 'create_date']
                for name in fallback_names:
                    found = self.env['ir.model.fields'].search([
                        ('model_id', '=', self.model_id.id),
                        ('name', '=', name),
                        ('ttype', 'in', ('date', 'datetime'))
                    ], limit=1)
                    if found:
                        date_field = found
                        break

            if not date_field:
                return []

            field_name = date_field.name
            prev_domain = []
            prev_domain.append((field_name, '>=', fields.Date.to_string(prev_start)))
            if date_field.ttype == 'datetime':
                prev_domain.append((field_name, '<=', f"{fields.Date.to_string(prev_end)} 23:59:59"))
            else:
                prev_domain.append((field_name, '<=', fields.Date.to_string(prev_end)))
            
            return prev_domain
        except Exception as e:
            _logger.error("Error calculating previous period domain: %s", e)
            return []

    @api.model
    def action_clear_dashboard(self, dashboard_id):
        """Delete all widgets for a specific dashboard."""
        widgets = self.search([('dashboard_id', '=', dashboard_id)])
        if widgets:
            widgets.unlink()
        return True

    def action_open_filtered_records(self, date_filter=None, extra_domain=None):
        """Open the widget records using the same domain as the dashboard tile."""
        self.ensure_one()

        base_domain = safe_eval(self.filter) if self.filter else []
        domain = list(base_domain)
        domain += self._get_date_domain(date_filter)

        if extra_domain:
            domain += extra_domain

        return {
            'type': 'ir.actions.act_window',
            'name': f"Records for {self.name or 'Widget'}",
            'res_model': self.model_name,
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
            'target': 'current',
        }

    def action_get_chart_insight(self, date_filter=None):
        """Aggregate data for THIS specific chart and get an AI-generated summary."""
        self.ensure_one()

        api_key = self.env['ir.config_parameter'].sudo().get_param('multi_dashboard.gemini_api_key')
        if not api_key:
            return {'success': False, 'error': 'Gemini API Key is not configured. Please add it in General Settings.'}

        try:
            widget_data = self.get_widget_value(date_filter=date_filter)

            # Simplify data for AI context
            simplified_data = {
                'chart_name': self.name,
                'chart_type': self.chart_type,
                'model': self.model_id.name,
                'data_points': []
            }

            if self.chart_type in ['tile', 'progress']:
                simplified_data['value'] = widget_data.get('value', widget_data.get('current_value', 0))
            elif self.chart_type == 'list':
                simplified_data['data_points'] = widget_data.get('records', [])[:5]
            elif isinstance(widget_data.get('data'), list):
                simplified_data['data_points'] = widget_data.get('data')

            client = genai.Client(api_key=api_key)

            # Dynamic model selection
            model_name = 'gemini-1.5-flash'
            try:
                available_models = [m.name for m in client.models.list()]
                flash_models = [m for m in available_models if 'flash' in m.lower()]
                if flash_models:
                    model_name = flash_models[0].replace('models/', '')
            except Exception:
                pass

            prompt = f"""
            Analyze the following data for the individual chart "{self.name}" from an Odoo dashboard.
            Model: {self.model_id.name}
            Chart Type: {self.chart_type}
            
            Data (JSON):
            {json.dumps(simplified_data, indent=2, default=str)}
            
            Provide a CONCISE insight (max 3 sentences) explaining:
            1. What this data currently tells us.
            2. Any notable trend or outlier.
            3. A quick recommended action.
            
            Be direct and analytical. No fluff.
            """

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return {'success': True, 'summary': response.text}

        except Exception as e:
            return {'success': False, 'error': f'Insight Generation Failed: {str(e)}'}


    def _get_amcharts_data(self, date_domain=None):
        """
        Main entry point for fetching chart data.
        Routes to appropriate method based on chart type.
        """
        model = self.env[self.model_name]
        domain = safe_eval(self.filter) if self.filter else []
        if date_domain:
            domain += date_domain

        if not self.chart_group_field_id:
            return {'error': "Please configure a 'Group By' field."}

        # Route to appropriate chart type handler
        if self.chart_type == 'donut' and self.chart_sub_group_field_id:
            return self._get_bar_line_chart_data(model, domain)

        elif self.chart_type in ['pie', 'donut']:
            return self._get_pie_chart_data(model, domain)

        elif self.chart_type in ['bar', 'line', 'radar', 'stacked', 'radialBar',
                                 'scatter']:
            return self._get_bar_line_chart_data(model, domain)

        elif self.chart_type in ['funnel', 'pyramid']:
            return self._get_funnel_pyramid_chart_data(model, domain)

        else:
            return {'error': f"Unsupported chart type: {self.chart_type}"}

    def _prepare_common_data(self, model, domain):
        """
        Prepare common data structures needed for all chart types.
        Returns: dict with group_field, fields_to_read, measure_fields, etc.
        """
        group_field = self.chart_group_field_id.name
        group_field_param = group_field

        if self.chart_group_field_id.ttype in ['date',
                                               'datetime'] and self.chart_date_group_by:
            group_field_param = f"{group_field}:{self.chart_date_group_by}"

        fields_to_read = [group_field]
        measure_fields = []

        if self.measure_aggregation != 'count':
            if self.chart_type in ['pie', 'pyramid', 'funnel']:
                if self.measure_field_id:
                    fields_to_read.append(self.measure_field_id.name)
                    measure_fields.append(self.measure_field_id.name)
                else:
                    return {
                        'error': "Please select Measure field for Pie."}
            else:
                if not self.chart_measure_field_ids:
                    return {
                        'error': "Please select at least one Measure field."}

                for f in self.chart_measure_field_ids:
                    fields_to_read.append(f.name)
                    measure_fields.append(f.name)

        # Pre-fetch selection labels
        selection_labels = {}
        if self.chart_group_field_id.ttype == 'selection':
            selection_labels = dict(model._fields[group_field].selection)

        return {
            'group_field': group_field,
            'group_field_param': group_field_param,
            'fields_to_read': fields_to_read,
            'measure_fields': measure_fields,
            'selection_labels': selection_labels
        }

    def _get_raw_value(self, raw_label, field):
        """Extract the raw ID or value for filtering."""
        if not raw_label:
            return False

        if field.ttype == 'many2one':
            if hasattr(raw_label, 'id'):
                return raw_label.id
            elif isinstance(raw_label, (list, tuple)) and len(raw_label) > 0:
                return raw_label[0]
            return raw_label
        return raw_label

    def _format_label(self, raw_label, field, selection_labels):
        """
        Format a label based on field type.
        Updated to handle Odoo 19 _read_group Recordset returns.
        """
        if not raw_label:
            return "Undefined"

        if field.ttype == 'many2one':
            # 1. Handle New _read_group (Returns a Recordset)
            if hasattr(raw_label, 'display_name'):
                return raw_label.display_name

            # 2. Handle Legacy read_group (Returns a Tuple)
            elif isinstance(raw_label, tuple) and len(raw_label) >= 2:
                return raw_label[1]

            # 3. Handle IDs or Strings
            elif isinstance(raw_label, (int, str)):
                return str(raw_label)
            else:
                return "Undefined"

        elif field.ttype == 'selection':
            return selection_labels.get(raw_label, raw_label)
        else:
            return str(raw_label)

    def _get_funnel_pyramid_chart_data(self, model, domain):
        """
        Fetch data specifically for Funnel/Pyramid charts.
        Creates one data point per category with single value.
        Funnel charts are used to show stages in a process (e.g., sales funnel).
        Pyramid charts are similar but inverted visualization.
        """
        common = self._prepare_common_data(model, domain)
        if 'error' in common:
            return common

        group_field = common['group_field']
        group_field_param = common['group_field_param']
        measure_fields = common['measure_fields']
        selection_labels = common['selection_labels']

        # Prepare aggregates: Count is always needed, plus sum for measure field (singular)
        aggregates = ['__count']
        if measure_fields:
            # Funnel/Pyramid use single measure field
            aggregates.append(f"{measure_fields[0]}:sum")

        groupby = [group_field_param]

        # Execute read_group
        # Returns a list of tuples: (group_val, count, measure_sum)
        raw_groups = model._read_group(
            domain,
            groupby=groupby,
            aggregates=aggregates
        )

        # Convert _read_group tuple results to list of dicts
        groups = []
        for result in raw_groups:
            group_item = {
                group_field: result[0],
                group_field_param: result[0],
                '__count': result[1]
            }

            # Map measure sum back to field name (single measure)
            if measure_fields:
                group_item[measure_fields[0]] = result[2]

            groups.append(group_item)

        chart_data = []

        # Process each group into chart data
        for group in groups:
            raw_label = group.get(group_field)
            label = self._format_label(raw_label, self.chart_group_field_id,
                                       selection_labels)
            raw_val = self._get_raw_value(raw_label, self.chart_group_field_id)

            if self.measure_aggregation == 'count':
                value = group.get('__count', 0)
            else:
                # Use single measure field value for funnel/pyramid
                count = group.get('__count', 1)
                field_name = measure_fields[0]
                val = group.get(field_name, 0) or 0

                if self.measure_aggregation == 'avg':
                    value = round(val / count, 2) if count > 0 else 0
                else:  # sum
                    value = round(val, 2)

            chart_data.append({
                'category': label,
                'raw_value': raw_val,
                'value': value
            })

        # Sort data for funnel (typically descending order)
        if self.chart_type == 'funnel':
            chart_data.sort(key=lambda x: x['value'], reverse=True)

        # Series config for single value (using singular measure_field_id)
        if measure_fields:
            series_name = self.measure_field_id.field_description
        else:
            series_name = 'Count'

        series_config = [{
            'valueField': 'value',
            'name': series_name
        }]

        return {
            'chart_type': self.chart_type,
            'data': chart_data,
            'series': series_config,
            'name': self.name,
            'has_sub_group': False,
            'orientation': self.chart_orientation,
            'groupField': self.chart_group_field_id.name,
            'groupFieldLabel': self.chart_group_field_id.field_description,
            'measureFieldLabel': self.measure_field_id.field_description if self.measure_field_id else 'Count',
        }

    def _get_pie_chart_data(self, model, domain):
        """
        Fetch data specifically for Pie/Donut charts.
        Creates one data point per category with single value.
        """
        common = self._prepare_common_data(model, domain)
        if 'error' in common:
            return common

        group_field = common['group_field']
        group_field_param = common['group_field_param']
        measure_fields = common['measure_fields']
        selection_labels = common['selection_labels']

        # Prepare aggregates: Count is always needed, plus sum for any measure fields
        aggregates = ['__count']
        for field_name in measure_fields:
            aggregates.append(f"{field_name}:sum")

        groupby = [group_field_param]

        # Execute read_group
        # Returns a list of tuples: (group_val, count, measure1_sum, measure2_sum...)
        raw_groups = model._read_group(
            domain,
            groupby=groupby,
            aggregates=aggregates
        )

        # Convert _read_group tuple results to list of dicts to match original logic
        groups = []
        for result in raw_groups:
            # result[0] is the group value
            # result[1] is the count
            # result[2:] are the measure sums
            group_item = {
                group_field: result[0],  # Used by pie chart logic
                group_field_param: result[0],  # Redundant safety
                '__count': result[1]
            }

            # Map measure sums back to field names
            for i, field_name in enumerate(measure_fields):
                group_item[field_name] = result[2 + i]

            groups.append(group_item)

        chart_data = []
        series_config = []

        # Check if this is a multi-measure donut (not pie, and multiple measures)
        is_multi_measure_donut = (
                self.chart_type == 'donut' and
                self.measure_aggregation != 'count' and
                len(measure_fields) > 1
        )

        if is_multi_measure_donut:
            # For multi-measure donut: create separate value fields for each measure
            for group in groups:
                raw_label = group.get(group_field)
                label = self._format_label(raw_label, self.chart_group_field_id,
                                           selection_labels)

                data_point = {'category': label}
                count = group.get('__count', 1)

                # Add each measure as a separate field
                for field_name in measure_fields:
                    val = group.get(field_name, 0) or 0
                    if self.measure_aggregation == 'avg':
                        val = val / count if count > 0 else 0
                    data_point[field_name] = round(val, 2)

                chart_data.append(data_point)

            # Create series config for each measure
            for f in self.chart_measure_field_ids:
                series_config.append({
                    'valueField': f.name,
                    'name': f.field_description
                })
        else:
            # Original logic for pie chart or single-measure donut
            for group in groups:
                raw_label = group.get(group_field)
                label = self._format_label(raw_label, self.chart_group_field_id,
                                           selection_labels)

                if self.measure_aggregation == 'count':
                    value = group.get('__count', 0)
                else:
                    # Sum all measures together for single-value pie/donut
                    count = group.get('__count', 1)
                    total_value = 0

                    for field_name in measure_fields:
                        val = group.get(field_name, 0) or 0
                        if self.measure_aggregation == 'avg':
                            val = val / count if count > 0 else 0
                        total_value += val

                    value = round(total_value, 2)

                chart_data.append({
                    'category': label,
                    'raw_value': self._get_raw_value(raw_label, self.chart_group_field_id),
                    'value': value
                })

            # Series config for single value
            if measure_fields:
                series_name = self.measure_field_id.field_description if self.chart_type == 'pie' else \
                    self.chart_measure_field_ids[0].field_description
            else:
                series_name = 'Count'

            series_config = [{
                'valueField': 'value',
                'name': series_name
            }]
        return {
            'chart_type': self.chart_type,
            'data': chart_data,
            'series': series_config,
            'name': self.name,
            'has_sub_group': False,
            'groupField': self.chart_group_field_id.name,
            'groupFieldLabel': self.chart_group_field_id.field_description,
            'measureFieldLabel': self.measure_field_id.field_description if self.measure_field_id else 'Count',
        }

    def _get_bar_line_chart_data(self, model, domain):
        """
        Fetch data for Bar/Line charts.
        Fixed: Consolidates multiple measures into a single data point per category.
        """
        common = self._prepare_common_data(model, domain)
        if 'error' in common:
            return common

        group_field_param = common['group_field_param']
        measure_fields = common['measure_fields']
        selection_labels = common['selection_labels']

        # Build groupby list with optional sub-group
        groupby_list = [group_field_param]
        sub_group_field = None
        sub_group_field_param = None

        if self.chart_sub_group_field_id:
            sub_group_field = self.chart_sub_group_field_id.name
            sub_group_field_param = sub_group_field
            groupby_list.append(sub_group_field_param)

        aggregates = ['__count']
        for field_name in measure_fields:
            aggregates.append(f"{field_name}:sum")

        # Fetch Data
        raw_groups = model._read_group(
            domain,
            groupby=groupby_list,
            aggregates=aggregates
        )

        # Pre-fetch sub-group selection labels
        sub_selection_labels = {}
        if sub_group_field and self.chart_sub_group_field_id.ttype == 'selection':
            sub_selection_labels = dict(
                model._fields[sub_group_field].selection)

        groups = []
        for result in raw_groups:
            group_item = {}
            for i, key in enumerate(groupby_list):
                group_item[key] = result[i]

            agg_index_start = len(groupby_list)
            group_item['__count'] = result[agg_index_start]

            for i, field_name in enumerate(measure_fields):
                group_item[field_name] = result[agg_index_start + 1 + i]
            groups.append(group_item)

        # Process groups into chart data
        chart_data = []
        series_names = set()

        for group in groups:
            raw_label = group.get(group_field_param)
            label = self._format_label(raw_label, self.chart_group_field_id,
                                       selection_labels)
            raw_val = self._get_raw_value(raw_label, self.chart_group_field_id)

            # Initialize ONE data point for this group row
            data_point = {'category': label, 'raw_value': raw_val}

            # Process Sub-Group Label
            sub_label = None
            if sub_group_field:
                raw_sub_label = group.get(sub_group_field_param)
                sub_label = self._format_label(
                    raw_sub_label,
                    self.chart_sub_group_field_id,
                    sub_selection_labels
                )

            # Process Values
            if self.measure_aggregation == 'count':
                value = group.get('__count', 0)
                if sub_label:
                    series_names.add(sub_label)
                    data_point[sub_label] = value
                else:
                    data_point['value'] = value
                # Append inside if/else only if structure differs significantly,
                # but usually easier to append at the end.
                # For count, structure is simple, so we can append here or unify logic.
                # Keeping your count logic structure but utilizing the single data_point:
                chart_data.append(data_point)

            else:
                # Multi-Measure Logic
                count = group.get('__count', 1)

                # 2. Iterate measures and update the SAME data_point dictionary
                for field_name in measure_fields:
                    val = group.get(field_name, 0) or 0

                    if self.measure_aggregation == 'avg':
                        val = val / count if count > 0 else 0

                    if sub_label:
                        series_key = f"{field_name}_{sub_label}"
                        series_names.add((field_name, sub_label))
                        data_point[series_key] = round(val, 2)
                    else:
                        # Direct assignment for multi-measure stacking
                        data_point[field_name] = round(val, 2)

                # 3. Append the consolidated dictionary ONCE after the loop
                chart_data.append(data_point)

        # Merge data points with same category (Required for Sub-Groups)
        if sub_group_field:
            chart_data = self._merge_chart_data(chart_data)

        # Build series configuration
        series_config = self._build_series_config(
            measure_fields,
            series_names,
            sub_group_field
        )

        return {
            'chart_type': self.chart_type,
            'data': chart_data,
            'series': series_config,
            'name': self.name,
            'has_sub_group': bool(sub_group_field),
            'groupField': self.chart_group_field_id.name,
            'groupFieldType': self.chart_group_field_id.ttype,
            'date_granularity': self.chart_date_group_by if self.chart_group_field_id.ttype in ['date', 'datetime'] else False,
            'groupFieldLabel': self.chart_group_field_id.field_description,
        }

    def _merge_chart_data(self, chart_data):
        """
        Merge data points that share the same category.
        Used for sub-grouped bar/line charts.
        """
        merged_data = {}
        for point in chart_data:
            cat = point['category']
            if cat not in merged_data:
                merged_data[cat] = {'category': cat}
            merged_data[cat].update(
                {k: v for k, v in point.items() if k != 'category'}
            )
        return list(merged_data.values())

    def _build_series_config(self, measure_fields, series_names,
                             sub_group_field):
        """
        Build series configuration for bar/line charts.
        """
        series_config = []

        if self.measure_aggregation == 'count':
            if sub_group_field:
                for sub_name in sorted(series_names):
                    series_config.append({
                        'valueField': sub_name,
                        'name': sub_name
                    })
            else:
                series_config.append({
                    'valueField': 'value',
                    'name': 'Count'
                })
        else:
            if sub_group_field:
                for field_name, sub_name in sorted(series_names):
                    field_obj = self.chart_measure_field_ids.filtered(
                        lambda f: f.name == field_name
                    )
                    series_config.append({
                        'valueField': f"{field_name}_{sub_name}",
                        'name': f"{field_obj.field_description} - {sub_name}"
                    })
            else:
                for f in self.chart_measure_field_ids:
                    series_config.append({
                        'valueField': f.name,
                        'name': f.field_description
                    })

        return series_config

    def _get_list_view_data(self, date_domain=None):
        """Get data for list view widget with Group By support"""
        self.ensure_one()
        if not self.model_name or not self.list_field_ids:
            return {'records': [], 'fields': []}

        try:
            domain = safe_eval(self.filter) if self.filter else []
            if date_domain:
                domain += date_domain
            model = self.env[self.model_name]

            # SORTING LOGIC
            sort_field = self.list_sort_field_id.name if self.list_sort_field_id else 'id'
            # Handle special case where display_name is selected but we sort by name
            if sort_field == "display_name":
                sort_field = "name"

            sort_dir = self.list_sort_direction or 'desc'
            order_clause = f"{sort_field} {sort_dir}"

            if self.list_group_field_id:
                group_field_name = self.list_group_field_id.name
                # Primary sort: Group Field (Ascending), Secondary: User selection
                order_clause = f"{group_field_name} asc, {order_clause}"

            # FETCH RECORDS
            limit = self.list_limit if self.list_limit > 0 else False
            records = model.search(domain, order=order_clause, limit=limit)

            # PREPARE FIELD DEFINITIONS
            fields_data = []
            ordered_field_defs = []

            for line in self.list_field_ids:
                field_def = line.field_id
                fields_data.append({
                    'index': line.sequence,
                    'name': field_def.name,
                    'label': field_def.field_description,
                    'type': field_def.ttype
                })
                ordered_field_defs.append(field_def)

            # PROCESS RECORDS
            processed_records = []

            for record in records:
                record_values = {'id': record.id}

                # Extract Column Values
                for field in ordered_field_defs:
                    field_name = field.name
                    val = record[field_name]

                    if field.ttype == 'many2one':
                        record_values[
                            field_name] = val.display_name if val else ''
                    elif field.ttype in ('one2many', 'many2many'):
                        record_values[field_name] = ', '.join(
                            val.mapped('display_name'))
                    elif field.ttype == 'boolean':
                        record_values[field_name] = 'Yes' if val else 'No'
                    elif field.ttype in ('date', 'datetime'):
                        record_values[field_name] = str(val) if val else ''
                    elif field.ttype == 'selection':
                        # Get the human-readable selection label
                        record_values[field_name] = dict(
                            record._fields[field_name].selection).get(
                            val) or val
                    else:
                        record_values[field_name] = val if val else ''

                # B. Extract Group Name (if grouping is active)
                if self.list_group_field_id:
                    g_field = self.list_group_field_id
                    g_val = record[g_field.name]

                    group_name = "Undefined"
                    if g_val:
                        if g_field.ttype == 'many2one':
                            group_name = g_val.display_name
                        elif g_field.ttype == 'selection':
                            group_name = dict(
                                record._fields[g_field.name].selection).get(
                                g_val) or g_val
                        elif g_field.ttype == 'boolean':
                            group_name = 'Yes' if g_val else 'No'
                        else:
                            group_name = str(g_val)

                    record_values['__group_name'] = group_name

                processed_records.append(record_values)

            final_data = []
            is_grouped = False

            if self.list_group_field_id and processed_records:
                is_grouped = True
                # Group by the extracted '__group_name'
                grouper = itemgetter('__group_name')

                # Note: Records are already sorted by group_field in the search query,
                # so we can safely use itertools.groupby directly.
                for key, grp in groupby(processed_records, grouper):
                    final_data.append({
                        'group_name': key,
                        'records': list(grp)
                    })
            else:
                final_data = processed_records

            return {
                'id': self.id,
                'name': self.name,
                'model': self.model_name,
                'records': final_data,
                'fields': sorted(fields_data, key=lambda f: f['index']),
                'row_clickable': self.list_row_clickable,
                'total_count': len(records),
                'limit_per_page': self.limit_per_page,
                'is_grouped': is_grouped,
                'todo_color': self.todo_color,
                'use_background_gradient': self.use_background_gradient,
            }

        except Exception as e:
            return {'records': [], 'fields': [], 'error': str(e)}

    @api.model
    def get_dashboard_widgets(self, dashboard_id):
        """ Fetch all widgets for a given dashboard ID, used to load the
         dashboard view with its charts. """
        widgets = self.sudo().search_read(
            [('dashboard_id', '=', int(dashboard_id))],
            []
        )
        return widgets

    @api.model
    def get_preview_data(self, config):
        """
        Computes chart data based on a provided configuration dictionary
        instead of a database record.
        """

        # Clean and prepare config data
        clean_config = {
            'name': config.get('name', 'Preview'),
            'chart_type': config.get('chart_type'),
            'model_id': config.get('model_id'),
            'filter': config.get('filter', '[]'),
            'measure_aggregation': config.get('measure_aggregation'),
            'measure_field_id': config.get('measure_field_id'),
            'widget_color': config.get('widget_color'),
            'layout_style': config.get('layout_style'),
            'tile_font_style': config.get('tile_font_style'),
            'font_color': config.get('font_color'),
            'todo_ids': config.get('todo_ids', []),
            'todo_color': config.get('todo_color', 4),
            'use_background_gradient': config.get('use_background_gradient', False),
            'list_field_ids': config.get('list_field_ids', []),
            'list_group_field_id': config.get('list_group_field_id'),
            'list_sort_field_id': config.get('list_sort_field_id'),
            'list_sort_direction': config.get('list_sort_direction', 'desc'),
            'list_limit': config.get('list_limit', 10),
            'limit_per_page': config.get('limit_per_page', 10),
            'list_row_clickable': config.get('list_row_clickable'),
            'chart_group_field_id': config.get('chart_group_field_id'),
            'chart_measure_field_ids': config.get('chart_measure_field_ids',
                                                  []),
            'chart_sub_group_field_id': config.get('chart_sub_group_field_id'),
            'chart_orientation': config.get('chart_orientation', 'vertical'),
            'am_chart_theme': config.get('am_chart_theme'),
            'tz': config.get('tz'),
            'clock_format': config.get('clock_format', '24'),
            'progress_target_static': config.get('progress_target_static'),
            'chart_date_group_by': config.get('chart_date_group_by'),
            'tile_icon': config.get('tile_icon'),
            'tile_unit_format': config.get('tile_unit_format', 'auto'),
        }

        # Remove None values
        clean_config = {k: v for k, v in clean_config.items() if v is not None}

        try:
            # Create an in-memory record from the config dict
            mock_record = self.new(clean_config)

            # Reuse your existing routing logic
            return mock_record.get_widget_value()
        except Exception as e:
            return {'error': str(e), 'value': 0}

    @api.model
    def export_to_json(self, dashboard_id=None, chart_id=None):
        """Export the chart configuration as a JSON string"""
        charts = []
        export_name = "export"

        if dashboard_id:
            dashboard = self.env['multi.dashboards'].browse(int(dashboard_id))
            charts = self.env['multi.dashboard.charts'].search(
                [('dashboard_id', '=', dashboard.id)])
            export_name = dashboard.name
        elif chart_id:
            charts = self.env['multi.dashboard.charts'].browse(int(chart_id))
            export_name = charts.name

        if not charts:
            return False
        chart_data_list = []
        for chart in charts:
            config = {
                'name': chart.name,
                'chart_type': chart.chart_type,
                'model_id': chart.model_id.id if chart.model_id else None,
                'filter': chart.filter,
                'measure_aggregation': chart.measure_aggregation,
                'measure_field_id': chart.measure_field_id.id if chart.measure_field_id else None,
                'widget_color': chart.widget_color,
                'layout_style': chart.layout_style,
                'tile_font_style': chart.tile_font_style,
                'font_color': chart.font_color,
                'todo_ids': [
                    {
                        'name': todo.name,
                        'sequence': todo.sequence,
                        'is_done': todo.is_done,
                    } for todo in chart.todo_ids
                ],
                'todo_color': chart.todo_color,
                'list_field_ids': [
                    {
                        'field_id': field.field_id.id,
                        'sequence': field.sequence,
                    } for field in chart.list_field_ids
                ],
                'list_group_field_id': chart.list_group_field_id.id if chart.list_group_field_id else None,
                'list_sort_field_id': chart.list_sort_field_id.id if chart.list_sort_field_id else None,
                'list_sort_direction': chart.list_sort_direction,
                'list_limit': chart.list_limit,
                'limit_per_page': chart.limit_per_page,
                'list_row_clickable': chart.list_row_clickable,
                'chart_group_field_id': chart.chart_group_field_id.id if chart.chart_group_field_id else None,
                'chart_measure_field_ids': chart.chart_measure_field_ids.ids,
                'chart_sub_group_field_id': chart.chart_sub_group_field_id.id if chart.chart_sub_group_field_id else None,
                'chart_orientation': chart.chart_orientation,
                'progress_target_static': chart.progress_target_static,
                'chart_date_group_by': chart.chart_date_group_by,
                'gs_x': chart.gs_x,
                'gs_y': chart.gs_y,
                'gs_w': chart.gs_w,
                'gs_h': chart.gs_h,
                'is_kpi': chart.is_kpi,
                'kpi_comparison': chart.kpi_comparison,
                'use_background_gradient': chart.use_background_gradient,
            }
            chart_data_list.append(config)
        return {
            'filename': f"{export_name.replace(' ', '_')}.json",
            'content': json.dumps(chart_data_list)
        }
