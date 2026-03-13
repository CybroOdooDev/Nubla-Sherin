# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        session = config.current_session_id
        if not config.module_pos_hr or not config.time_log or not session or not session.task_id:
            return False

        return [
            ('task_id', '=', session.task_id.id),
            ('date', '=', fields.Date.context_today(self)),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['employee_id', 'unit_amount']
