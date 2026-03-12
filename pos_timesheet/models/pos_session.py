# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Ashwin T (odoo@cybrosysy.com)
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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


import logging
import datetime

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    """Inherits the PosSession class for adding fields and functions"""
    _inherit = 'pos.session'

    task_id = fields.Many2one("project.task", string="Task",
                              help="Session Timesheet Task",
                              required=True, ondelete='cascade', default=False)

    def _validate_time_log_project(self):
        for session in self.filtered(lambda s: s.config_id.module_pos_hr and s.config_id.time_log):
            project = session.config_id.project_id
            if not project:
                raise ValidationError(_("Please configure a project for POS time logging."))
            if not project.allow_timesheets or not project.account_id:
                raise ValidationError(_(
                    "The selected project must have Timesheets enabled and an analytic account."
                ))

    def _get_project_sequence(self):
        self.ensure_one()
        return self.search_count([
            ('config_id.project_id', '=', self.config_id.project_id.id),
            ('id', '<=', self.id),
        ])

    def _get_time_log_sequence(self):
        self.ensure_one()
        return self.search_count([
            ('config_id', '=', self.config_id.id),
            ('id', '<=', self.id),
        ])

    def _get_project_session_name(self):
        self.ensure_one()
        return f"{self.config_id.project_id.display_name}/{self._get_project_sequence():05d}"

    def _get_time_log_task_name(self):
        self.ensure_one()
        return f"{self.config_id.display_name}/{self._get_time_log_sequence():05d}"

    def _ensure_time_log_task(self):
        sessions_needing_task = self.filtered(
            lambda s: s.config_id.module_pos_hr and s.config_id.time_log
        )
        if not sessions_needing_task:
            return

        existing_tasks = self.env['project.task'].sudo().search([
            ('pos_session_id', 'in', sessions_needing_task.ids),
        ])
        task_by_session = {task.pos_session_id.id: task for task in existing_tasks}
        sessions_missing_task = self.env['pos.session']
        vals_list = []

        for session in sessions_needing_task:
            existing_task = task_by_session.get(session.id) or session.task_id
            if existing_task:
                session.task_id = existing_task.id
                continue

            sessions_missing_task |= session
            vals_list.append({
                'name': session._get_time_log_task_name(),
                'project_id': session.config_id.project_id.id,
                'company_id': session.config_id.company_id.id,
                'pos_session_id': session.id,
            })

        if vals_list:
            created_tasks = self.env['project.task'].sudo().create(vals_list)
            for session, task in zip(sessions_missing_task, created_tasks):
                session.task_id = task.id

    @api.model_create_multi
    def create(self, vals_list):
        """Create the session and create the task if required"""
        sessions = super().create(vals_list)
        sessions._validate_time_log_project()
        sessions._ensure_time_log_task()
        return sessions

    def set_opening_control(self, cashbox_value: int, notes: str):
        result = super().set_opening_control(cashbox_value, notes)
        for session in self.filtered(lambda s: s.config_id.module_pos_hr and s.config_id.time_log):
            session._validate_time_log_project()
            session._ensure_time_log_task()
            session.name = session._get_project_session_name()
            if session.task_id:
                session.task_id.name = session._get_time_log_task_name()
        return result

    def _pos_ui_models_to_load(self):
        """loads models to the UI"""
        result = super()._pos_ui_models_to_load()
        result.append('account.analytic.line')
        return result

    def _loader_params_account_analytic_line(self):
        """Returns loader params for account"""
        return {
            'search_params': {
                'domain': [('task_id', '=', self.task_id.id),
                           ('date', '=', fields.Date.context_today(self))],
                'fields': ['employee_id', 'unit_amount'],
            },
        }

    def _get_pos_ui_account_analytic_line(self, params):
        """Returns the account analytics line for the pos"""
        return self.env['account.analytic.line'].search_read(**params['search_params'])


    def _loader_params_pos_session(self):
        """Loading parameters to the session"""
        result = super()._loader_params_pos_session()
        result['search_params']['fields'].append('task_id')
        return result

    def set_timesheet(self, data):
        """Update Timesheet of the employee"""
        _logger.info("Setting timesheet for session(s): %s with data: %s", self.ids, data)
        try:
            AnalyticLine = self.env['account.analytic.line'].sudo()
            for timesheet in data:
                if timesheet.get('workMinutes', 0) > 0:
                    hours = timesheet['workMinutes'] / 60
                    session_id = self.sudo().browse(timesheet.get('sessionId')) or self.sudo()
                    if not session_id.exists():
                        _logger.error("No session found for timesheet data: %s", timesheet)
                        continue

                    if not session_id.task_id:
                        _logger.error("Session %s has no task_id assigned.", session_id.id)
                        continue

                    try:
                        session_id._validate_time_log_project()
                    except ValidationError as e:
                        _logger.error("Validation failed for session %s: %s", session_id.id, e)
                        continue

                    timestamp_seconds = timesheet['checkInTime'] / 1000
                    date_time = datetime.datetime.fromtimestamp(timestamp_seconds)
                    date_only = date_time.date()
                    project = session_id.config_id.project_id
                    timesheet_name = f"{session_id.name} - {session_id.task_id.name}"
                    employee = self.env['hr.employee'].sudo().browse(timesheet['cashierId'])

                    if not employee.exists():
                        _logger.error("No employee found with ID: %s", timesheet['cashierId'])
                        continue

                    employee_timesheet = AnalyticLine.search(
                        [('task_id', '=', session_id.task_id.id),
                         ('date', '=', date_only),
                         ('employee_id', '=', employee.id),
                         ('project_id', '=', project.id)], limit=1)

                    if employee_timesheet:
                        employee_timesheet.write({
                            'project_id': project.id,
                            'task_id': session_id.task_id.id,
                            'account_id': project.account_id.id,
                            'employee_id': employee.id,
                            'user_id': employee.user_id.id or self.env.user.id,
                            'company_id': session_id.company_id.id,
                            'name': timesheet_name,
                            'unit_amount': employee_timesheet.unit_amount + hours,
                        })
                        _logger.info("Updated timesheet line %s with %s hours", employee_timesheet.id, hours)
                    else:
                        new_line = AnalyticLine.create({
                            'project_id': project.id,
                            'account_id': project.account_id.id,
                            'task_id': session_id.task_id.id,
                            'employee_id': employee.id,
                            'user_id': employee.user_id.id or self.env.user.id,
                            'name': timesheet_name,
                            'date': date_only,
                            'unit_amount': hours,
                            'company_id': session_id.company_id.id,
                            'product_uom_id': session_id.company_id.project_time_mode_id.id,
                        })
                        _logger.info("Created new timesheet line %s for employee %s", new_line.id, employee.id)
            return True
        except Exception as e:
            _logger.exception("Error in set_timesheet: %s", e)
            raise ValidationError(str(e))

    def show_time_log(self):
        """Show the task its contained timesheet for the session"""
        return {
            'name': _('Time Log'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.task_id.id,
        }


class ProjectTask(models.Model):
    _inherit = 'project.task'

    pos_session_id = fields.Many2one(
        'pos.session',
        string="POS Session",
        copy=False,
        index=True,
        ondelete='cascade',
    )
