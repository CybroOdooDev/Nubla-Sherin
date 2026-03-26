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

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class MultiDashboardAlert(models.Model):
    _name = 'multi.dashboard.alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dashboard Notification Alert'

    name = fields.Char('Alert Name', required=True)
    chart_id = fields.Many2one('multi.dashboard.charts', string='Dashboard Widget', required=True, ondelete='cascade')
    condition = fields.Selection([
        ('greater', 'Greater Than'),
        ('less', 'Less Than'),
        ('equal', 'Equal To')
    ], string='Condition', required=True, default='greater')
    value = fields.Float('Threshold Value', required=True)
    user_ids = fields.Many2many('res.users', string='Users to Notify', required=True, default=lambda self: self.env.user)
    is_active = fields.Boolean('Is Active', default=True)
    is_acknowledged = fields.Boolean('Acknowledged', default=False)
    last_triggered_value = fields.Float('Last Triggered Value', readonly=True)

    @api.model
    def _check_alerts(self):
        """Cron job to check all active alerts"""
        active_alerts = self.search([('is_active', '=', True)])
        for alert in active_alerts:
            # We pass empty date_filter to get the current overall value
            widget_data = alert.chart_id.get_widget_value()
            
            # Extract numerical value from widget data
            # Note: get_widget_value returns formatted strings for tiles, 
            # we might need to recalculate or get the raw value.
            # Looking at get_widget_value implementation, it calculates 'value' but returns 'display_value'.
            # I should probably add a way to get the raw value or just recalculate here.
            
            raw_value = self._get_raw_widget_value(alert.chart_id)
            
            if self._check_condition(raw_value, alert.condition, alert.value):
                # Notify if value changed or if it was never triggered/was acknowledged
                if raw_value != alert.last_triggered_value or alert.is_acknowledged:
                    alert._send_notification(raw_value)
                    alert.write({
                        'last_triggered_value': raw_value,
                        'is_acknowledged': False,
                    })
                else:
                    _logger.info("Alert %s already triggered with value %s, skipping repeat notification.", alert.name, raw_value)

    def _get_raw_widget_value(self, chart):
        """Helper to get the raw numerical value of a widget"""
        # This is a simplified version of get_widget_value logic
        domain = []
        if chart.filter:
            from odoo.tools.safe_eval import safe_eval
            domain = safe_eval(chart.filter)
        
        model = self.env[chart.model_name]
        field_name = chart.measure_field_id.name if chart.measure_field_id else None
        
        records = model.search(domain)
        if chart.measure_aggregation == 'count':
            return len(records)
        elif chart.measure_aggregation in ['sum', 'avg'] and field_name:
            values = records.mapped(field_name)
            if chart.measure_aggregation == 'sum':
                return sum(values) if values else 0
            else:
                return sum(values) / len(values) if values else 0
        return 0

    def _check_condition(self, current_value, condition, threshold):
        if condition == 'greater':
            return current_value > threshold
        elif condition == 'less':
            return current_value < threshold
        elif condition == 'equal':
            return current_value == threshold
        return False

    def _send_notification(self, current_value):
        """Send internal notification to users"""
        # Plain text for bus popup
        plain_body = _('Dashboard Alert: %s triggered with value %s') % (self.name, current_value)
        # HTML for Messaging/Bell icon
        html_body = _('<b>Dashboard Alert Triggered!</b><br/>'
                 '<b>Alert Name:</b> %s<br/>'
                 '<b>Widget:</b> %s<br/>'
                 '<b>Current Value:</b> %s<br/>'
                 '<b>Threshold Condition:</b> %s %s') % (
            self.name, self.chart_id.name, current_value, self.condition, self.value)
        
        for user in self.user_ids:
            # This ensures it appears in the Messaging menu (bell icon) and inbox (HTML supported)
            self.chart_id.message_notify(
                body=html_body,
                partner_ids=user.partner_id.ids,
                subject=_('Dashboard Alert: %s') % self.name,
            )
            
            # Also create an activity for the user (on the alert record itself)
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_('Dashboard Alert Triggered'),
                note=_('The alert "%s" for widget "%s" was triggered with value %s.') % (self.name, self.chart_id.name, current_value)
            )

    @api.model
    def get_dashboard_notifications(self, dashboard_id=None):
        """Fetch triggered alerts for a specific dashboard"""
        dashboard_id = dashboard_id or self.env.context.get('dashboard_id')
        if not dashboard_id:
            return {'count': 0, 'notifications': []}
        
        # Find all alerts for widgets on this dashboard that have been triggered and NOT acknowledged
        alerts = self.search([
            ('chart_id.dashboard_id', '=', int(dashboard_id)),
            ('is_active', '=', True),
            ('last_triggered_value', '!=', 0),
            ('is_acknowledged', '=', False)
        ], order='write_date desc', limit=10)
        
        notifications = []
        for alert in alerts:
            notifications.append({
                'id': alert.id,
                'name': alert.name,
                'widget': alert.chart_id.name,
                'widget_id': alert.chart_id.id,
                'value': alert.last_triggered_value,
                'condition': alert.condition,
                'threshold': alert.value,
                'date': fields.Datetime.to_string(alert.write_date),
            })
            
        return {
            'count': len(alerts),
            'notifications': notifications
        }

    def action_dismiss_alert(self):
        """Dismiss the current alert notification and complete associated activities"""
        self.write({'is_acknowledged': True})
        # Find and mark activities as done
        activities = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('summary', '=', _('Dashboard Alert Triggered'))
        ])
        if activities:
            activities.action_feedback(feedback=_('Dismissed from Dashboard'))
        return True
