# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MultiDashboardDuplicateMove(models.TransientModel):
    _name = 'multi.dashboard.duplicate.move'
    _description = 'Duplicate or Move Dashboard Item'

    chart_id = fields.Many2one('multi.dashboard.charts', string="Dashboard Item", required=True)
    dashboard_id = fields.Many2one('multi.dashboards', string="Target Dashboard", required=True)
    action_type = fields.Selection([
        ('duplicate', 'Duplicate'),
        ('move', 'Move')
    ], string="Action", default='duplicate', required=True)

    def action_apply(self):
        self.ensure_one()
        
        # Detect target dashboard layout to adjust widget size/position
        target_layout = self.dashboard_id.dashboard_layout or 'layout_1'
        new_gs_w = self.chart_id.gs_w
        new_gs_x = 0
        
        if target_layout == 'layout_1': # Centered
            new_gs_w = 8
            new_gs_x = 2
        elif target_layout == 'layout_2': # Side-by-Side
            new_gs_w = 6
        elif target_layout == 'layout_3': # Grid
            new_gs_w = 4

        # Find the next available Y position in the target dashboard to avoid overlaps
        existing_widgets = self.env['multi.dashboard.charts'].search([
            ('dashboard_id', '=', self.dashboard_id.id)
        ])
        next_y = 0
        if existing_widgets:
            # We place it at the very bottom
            next_y = max(w.gs_y + w.gs_h for w in existing_widgets)

        if self.action_type == 'move':
            self.chart_id.write({
                'dashboard_id': self.dashboard_id.id,
                'gs_x': new_gs_x,
                'gs_y': next_y,
                'gs_w': new_gs_w,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Item moved successfully to %s') % self.dashboard_id.name,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            # Duplicate logic
            new_chart = self.chart_id.copy({
                'dashboard_id': self.dashboard_id.id,
                'gs_x': new_gs_x,
                'gs_y': next_y,
                'gs_w': new_gs_w,
                'name': _('%s (Copy)') % self.chart_id.name
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Item duplicated successfully to %s') % self.dashboard_id.name,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
