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
import base64
import json
from google import genai
from google.genai import types
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MultiDashboards(models.Model):
    """Model for Multi Dashboards configuration"""
    _name = 'multi.dashboards'
    _description = 'Multi Dashboards'
    _order = 'sequence, id desc'

    name = fields.Char('Name', required=True,
                       help='Name of the dashboard')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        help='Company for this dashboard'
    )
    parent_menu = fields.Many2one(
        'ir.ui.menu',
        'Parent Menu',
        domain=[("action", "=", False)],
        help='Parent menu under which the dashboard menu will be created. '
             'If not set, the menu will be created at root level.'
    )
    user_ids = fields.Many2many('res.users',
                                string='Users for mailing',
                                help='Users to receive dashboard reports via email')
    menu_icon = fields.Binary('Menu Icon',
                              help='Icon for the dashboard menu (ignored if Parent Menu is set)')
    allowed_groups = fields.Many2many(
        'res.groups',
        string='Allowed Groups',
        help='Groups that can see the dashboard menu. If empty, it will be visible to all users.'
    )
    menu_id = fields.Many2one(
        'ir.ui.menu',
        'Created Menu',
        readonly=True,
        copy=False,
        help='Reference to the menu created for this dashboard. '
             'It will be automatically deleted when the dashboard is deleted.'
    )
    sequence = fields.Integer('Sequence', default=10,
                              help='Sequence of the dashboard menu')
    chart_ids = fields.One2many('multi.dashboard.charts',
                                'dashboard_id',
                                'Charts',
                                help='Charts included in this dashboard')
    email_template_id = fields.Many2one(
        'mail.template',
        'Email Template',
        default=lambda self: self.env.ref(
            'multi_dashboard.email_template_dashboard_report', raise_if_not_found=False),
        help='Email template used for sending dashboard reports. '
             'If not set, a default template will be used.'
    )
    theme = fields.Selection([
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('purple', 'Purple')
    ], string='Theme', default='light',
        help='Visual theme for this specific dashboard')
    refresh_interval = fields.Selection([
        ('0', 'Off'),
        ('1', '1 Minute'),
        ('5', '5 Minutes'),
        ('10', '10 Minutes'),
        ('15', '15 Minutes'),
        ('30', '30 Minutes'),
    ], string='Refresh Interval', default='0',
        help="Automatically refresh dashboard widgets")

    @api.constrains('name')
    def _check_name(self):
        """Ensure that the dashboard name is not empty or just whitespace"""
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_('Dashboard name cannot be empty.'))

    def action_create_menu(self):
        """Create menu item dynamically"""
        self.ensure_one()

        if self.menu_id:
            raise UserError(_('Menu already exists for this dashboard.'))

        actions = self.env['ir.actions.client']
        menus = self.env['ir.ui.menu']

        action_vals = {
            'name': self.name,
            'tag': 'MultiDashboardClientAction',
            'params': {
                'dashboard_id': self.id,
                'dashboard_name': self.name,
                'theme': self.theme,
            },
            'context': {'active_id': self.id},
        }
        action = actions.sudo().create([action_vals])
        # Prepare menu values
        menu_vals = {
            'name': self.name,
            'parent_id': self.parent_menu.id if self.parent_menu else False,
            'action': 'ir.actions.client,%d' % action.id if action else False,
            'sequence': self.sequence,
            'is_from_multi_dashboard': True,
        }

        # Add icon if provided and no parent menu
        if self.menu_icon and not self.parent_menu:
            # Store icon as web_icon_data (base64 encoded)
            menu_vals['web_icon_data'] = base64.b64encode(
                base64.b64decode(self.menu_icon)).decode('ascii')

        # Add groups if specified
        if self.allowed_groups:
            menu_vals['groups_id'] = [(6, 0, self.allowed_groups.ids)]

        # Create the menu
        menu = menus.sudo().create([menu_vals])

        # Update the record with the created menu
        self.menu_id = menu.id

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def unlink(self):
        """Delete associated menu when dashboard is deleted"""
        menus_to_delete = self.mapped('menu_id')
        res = super(MultiDashboards, self).unlink()
        if menus_to_delete:
            menus_to_delete.sudo().unlink()
        return res

    @api.onchange('parent_menu')
    def _onchange_parent_menu(self):
        """Clear icon when parent menu is set"""
        if self.parent_menu:
            self.menu_icon = False

    @api.model
    def action_prepare_dashboard_mail(self, dashboard_id, pdf_base64,
                                      json_base64=False, json_filename=None):
        """Prepare the context for sending dashboard report via email"""
        dashboard = self.browse(dashboard_id)
        recipient_partners = dashboard.user_ids.mapped('partner_id')

        manager_group = self.env.ref('multi_dashboard.group_multi_dashboard_manager',
                                     raise_if_not_found=False)
        if manager_group:
            recipient_partners |= manager_group.user_ids.mapped('partner_id')
        if not recipient_partners:
            raise UserError(_("No recipients found (Users or Managers)."))

        attachment_ids = []
        pdf_attach = self.env['ir.attachment'].create([{
            'name': f'Dashboard_Report: {dashboard.name}.pdf',
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'multi.dashboards',
            'res_id': dashboard_id,
            'mimetype': 'application/pdf',
        }])
        attachment_ids.append(pdf_attach.id)

        if json_base64:
            json_attach = self.env['ir.attachment'].create([{
                'name': json_filename or 'dashboard_config.json',
                'type': 'binary',
                'datas': json_base64,
                'res_model': 'multi.dashboards',
                'res_id': dashboard_id,
                'mimetype': 'application/json',
            }])
            attachment_ids.append(json_attach.id)

        template = self.email_template_id or self.env.ref(
            'multi_dashboard.email_template_dashboard_report',
            raise_if_not_found=False)
        reply_to_email = self.env.user.email or self.env.company.email

        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Dashboard via Email'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'default_composition_mode': 'comment',
                'default_model': 'multi.dashboards',
                'default_res_ids': [dashboard_id],
                'default_use_template': bool(template),
                'default_template_id': template.id if template else False,
                'default_attachment_ids': [fields.Command.set(attachment_ids)],
                'default_partner_ids': [
                    fields.Command.set(recipient_partners.ids)],
                'default_reply_to': reply_to_email,
            }
        }

    def action_view_menu(self):
        """Redirect to the actual Dashboard Client Action"""
        self.ensure_one()

        return {
            'type': 'ir.actions.client',
            'tag': 'MultiDashboardClientAction',
            'target': 'current',
            'params': {
                'dashboard_id': self.id,
                'dashboard_name': self.name,
                'theme': self.theme,
            },
            'context': {
                'active_id': self.id,
            },
        }

    def action_open_dashboard_charts(self):
        """Open the charts of the dashboard"""
        self.ensure_one()

        return {
            'name': _('Dashboard Charts'),
            'type': 'ir.actions.act_window',
            'res_model': 'multi.dashboard.charts',
            'view_mode': 'list,form',
            'domain': [('dashboard_id', '=', self.id)],
            'context': {'default_dashboard_id': self.id},
        }

    @api.model
    def generate_chart_from_text(self, dashboard_id, query):
        """
        AI Parser to generate charts from a natural language query using Google Gemini.
        Example: "Create a dashboard for sale"
        """
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            return {'success': False, 'error': 'Dashboard not found'}

        api_key = self.env['ir.config_parameter'].sudo().get_param('multi_dashboard.gemini_api_key')
        if not api_key:
            return {'success': False, 'error': 'Gemini API Key is not configured. Please add it in General Settings.'}

        client = genai.Client(api_key=api_key)

        # Dynamic model selection to avoid 404 errors
        model_name = 'gemini-1.5-flash' # Default
        try:
            available_models = [m.name for m in client.models.list()]
            # Look for flash models first, then pro
            flash_models = [m for m in available_models if 'flash' in m.lower()]
            pro_models = [m for m in available_models if 'pro' in m.lower()]
            
            if flash_models:
                model_name = flash_models[0].replace('models/', '')
            elif pro_models:
                model_name = pro_models[0].replace('models/', '')
        except Exception:
            pass

        prompt = f"""
        Analyze the following user query for an Odoo MVP dashboard and generate appropriate charts:
        Query: "{query}"
        
        If the query implies multiple metrics or a full dashboard (e.g. "create a sales dashboard"), return a JSON array containing multiple JSON objects representing different, useful charts for that topic.
        If the query asks for just one specific chart, return a JSON array containing a single JSON object.
        
        Extract the following information for EACH chart and return ONLY a valid JSON ARRAY matching this schema exactly for each object:
        - name (string): A short, descriptive title for the chart.
        - chart_type (string): Type of chart. Must be one of: pie, bar, line, donut, list, tile, funnel, pyramid, radar, scatter, progress. Default: 'tile'.
        - model_name (string): The Odoo technical model name (e.g., sale.report, res.partner, crm.lead, account.move, product.template, project.task). Default to 'sale.report' for sales/revenue.
        - measure_field (string): The numeric field name to measure/aggregate (single field, e.g., price_total, Expected Revenue, amount_total, product_uom_qty, __count). Default: '__count'.
        - chart_measure_fields (array of strings): Applicable for charts supporting multiple measures (bar, line, radar, stacked, scatter, radialBar). Instead of `measure_field`, provide a list of numeric fields to measure (e.g., ["price_total", "margin"]).
        - progress_target_static (float): Applicable ONLY when chart_type is 'progress'. Set a static target value for the progress bar (e.g., 10000).
        - group_field (string): The category field name for the x-axis or grouping (e.g., partner_id, date, state, stage_id, user_id, product_id, categ_id). Default: 'create_date'.
        - limit (integer): Top N records to limit. Default: 10.
        """

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            ai_data = json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "API Quota Exceeded. Please wait a minute and try again."
            return {'success': False, 'error': f'AI Generation Failed ({model_name}): {error_msg}'}

        if isinstance(ai_data, dict):
            ai_data_list = [ai_data]
        elif isinstance(ai_data, list):
            ai_data_list = ai_data
        else:
            return {'success': False, 'error': 'Invalid AI response format'}

        created_charts = 0
        errors = []

        multi_measure_charts = ['bar', 'line', 'radar', 'stacked', 'scatter', 'radialBar', 'donut']

        for ai_obj in ai_data_list:
            chart_name = ai_obj.get('name', query.capitalize() or "Generated Chart")
            chart_type = ai_obj.get('chart_type', 'tile')
            target_model_key = ai_obj.get('model_name', 'sale.report')
            target_measure_key = ai_obj.get('measure_field', '__count')
            target_measure_keys = ai_obj.get('chart_measure_fields', [])
            progress_target = ai_obj.get('progress_target_static', 0.0)
            target_group_key = ai_obj.get('group_field', 'create_date')
            limit = ai_obj.get('limit', 10)

            ir_model = self.env['ir.model'].search([('model', '=', target_model_key)], limit=1)
            if not ir_model:
                errors.append(f'Model {target_model_key} not found')
                continue

            # Ensure measure field is valid and get aggregation
            measure_aggregation = 'sum'
            measure_field_id = False
            chart_measure_field_ids = []

            if chart_type in multi_measure_charts and target_measure_keys and isinstance(target_measure_keys, list):
                found_fields = self.env['ir.model.fields'].search([
                    ('model_id', '=', ir_model.id),
                    ('name', 'in', target_measure_keys),
                    ('ttype', 'in', ['integer', 'float', 'monetary'])
                ])
                if found_fields:
                    chart_measure_field_ids = [(6, 0, found_fields.ids)]
                    measure_field_id = found_fields[0].id
                else:
                    measure_aggregation = 'count'
            elif target_measure_key and target_measure_key != '__count':
                field = self.env['ir.model.fields'].search([
                    ('model_id', '=', ir_model.id),
                    ('name', '=', target_measure_key),
                    ('ttype', 'in', ['integer', 'float', 'monetary'])
                ], limit=1)
                if field:
                    measure_field_id = field.id
                    chart_measure_field_ids = [(6, 0, [field.id])]
                else:
                    measure_aggregation = 'count'
            else:
                measure_aggregation = 'count'

            # Ensure group field is valid
            group_field_id = False
            if target_group_key:
                field = self.env['ir.model.fields'].search([
                    ('model_id', '=', ir_model.id),
                    ('name', '=', target_group_key)
                ], limit=1)
                if field:
                    group_field_id = field.id

            # Domain / Filter
            domain = "[]"

            # Layout Calculation
            if chart_type in ['tile', 'todo', 'clock']:
                gs_w, gs_h = 3, 4
            elif chart_type == 'progress':
                gs_w, gs_h = 4, 3
            else:
                gs_w, gs_h = 6, 6

            # Create Chart
            vals = {
                'name': chart_name,
                'dashboard_id': dashboard.id,
                'chart_type': chart_type,
                'model_id': ir_model.id,
                'measure_aggregation': measure_aggregation,
                'filter': domain,
                'list_limit': limit,
                'gs_w': gs_w,
                'gs_h': gs_h
            }

            if chart_type == 'progress' and progress_target:
                try:
                    vals['progress_target_static'] = float(progress_target)
                except ValueError:
                    pass

            if measure_field_id:
                vals['measure_field_id'] = measure_field_id
                if chart_measure_field_ids:
                    vals['chart_measure_field_ids'] = chart_measure_field_ids

            if group_field_id:
                vals['chart_group_field_id'] = group_field_id
                vals['list_group_field_id'] = group_field_id
                if target_group_key == 'date' or 'month' in query.lower():
                    vals['chart_date_group_by'] = 'month'
                if 'day' in query.lower():
                    vals['chart_date_group_by'] = 'day'
                if 'year' in query.lower():
                    vals['chart_date_group_by'] = 'year'

            # Add basic list fields if chart_type is list
            if chart_type == 'list' and ir_model:
                list_fields = []
                if group_field_id:
                    list_fields.append((0, 0, {'field_id': group_field_id}))
                if measure_field_id:
                    list_fields.append((0, 0, {'field_id': measure_field_id}))
                if list_fields:
                    vals['list_field_ids'] = list_fields

            try:
                self.env['multi.dashboard.charts'].create([vals])
                created_charts += 1
            except Exception as e:
                errors.append(str(e))

        if created_charts > 0:
            return {'success': True, 'message': f'Generated {created_charts} charts.', 'errors': errors if errors else False}
        else:
            return {'success': False, 'error': f'Failed to generate any charts. Errors: {", ".join(errors)}'}
    @api.model
    def action_get_dashboard_summary(self, dashboard_id, date_filter=None):
        """
        Aggregate all chart data on the dashboard and get an AI-generated summary from Gemini.
        """
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            return {'success': False, 'error': 'Dashboard not found'}

        api_key = self.env['ir.config_parameter'].sudo().get_param('multi_dashboard.gemini_api_key')
        if not api_key:
            return {'success': False, 'error': 'Gemini API Key is not configured. Please add it in General Settings.'}

        charts = dashboard.chart_ids
        dashboard_data = []

        for chart in charts:
            try:
                # Use existing method to get chart data
                widget_data = chart.get_widget_value(date_filter=date_filter)
                
                # Simplify data for AI context to save tokens and improve focus
                simplified_data = {
                    'chart_name': chart.name,
                    'chart_type': chart.chart_type,
                    'model': chart.model_id.name,
                    'data_points': []
                }
                
                if chart.chart_type in ['tile', 'progress']:
                    simplified_data['value'] = widget_data.get('value', 0)
                elif chart.chart_type == 'list':
                    # Grab a few top records for context
                    simplified_data['data_points'] = widget_data.get('data', [])[:5]
                elif isinstance(widget_data.get('data'), list):
                    # For amCharts (pie, bar, line, etc.)
                    simplified_data['data_points'] = widget_data.get('data')
                
                dashboard_data.append(simplified_data)
            except Exception as e:
                continue

        if not dashboard_data:
            return {'success': False, 'error': 'No chart data available for analysis.'}

        client = genai.Client(api_key=api_key)

        # Dynamic model selection for summarization
        model_name = 'gemini-1.5-flash'
        try:
            available_models = [m.name for m in client.models.list()]
            flash_models = [m for m in available_models if 'flash' in m.lower()]
            pro_models = [m for m in available_models if 'pro' in m.lower()]
            
            if flash_models:
                model_name = flash_models[0].replace('models/', '')
            elif pro_models:
                model_name = pro_models[0].replace('models/', '')
        except Exception:
            pass

        prompt = f"""
        Act as a Senior Business Analyst. Analyze the data from the "{dashboard.name}" dashboard and provide a CONCISE, high-impact summary. Avoid fluff and long explanations.
        
        Dashboard Data (JSON):
        {json.dumps(dashboard_data, indent=2, default=str)}
        
        Structure your response exactly as follows:
        ## Quick Impact
        One punchy sentence on the overall health (e.g., "Revenue is soaring due to high-value orders, but customer acquisition is slowing.").
        
        ## Key Metrics
        3-5 bullet points highlighting the most critical trends or anomalies. Keep each point to one sentence.
        
        ## Strategic Moves
        2-3 high-priority, actionable recommendations based on the data.
        
        Formatting rules:
        - Use ## for section headers.
        - Be extremely concise. Maximum 2 sentences per section where applicable.
        - No introductory or concluding remarks.
        """

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            summary = response.text
            return {'success': True, 'summary': summary}
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "API Quota Exceeded. Please wait a minute and try again."
            return {'success': False, 'error': f'AI Summarization Failed ({model_name}): {error_msg}'}
