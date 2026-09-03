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

LOCKED_STATES = ('signed', 'revised')

TARGETS = [
    ('due', 'Plans Due'),
    ('unsigned', 'Unsigned Plans'),
    ('stale', 'Stale / Stalled Discussion'),
]


class NhsJobPlanReminderWizard(models.TransientModel):
    """On-demand counterpart to the daily reminder cron: preview and send
    reminders for plans due, unsigned, or stalled in discussion."""
    _name = 'nhs.job.plan.reminder.wizard'
    _description = 'Job Plan Reminder Wizard'

    target = fields.Selection(
        TARGETS,
        string='Remind About',
        required=True,
        default='due',
        help="Which plans to remind: due for review, unsigned, or stalled"
             " in proposed/discussion."
    )
    plan_year_id = fields.Many2one(
        'nhs.plan.year',
        string='Plan Year',
        help="Limit to a specific plan year. Leave blank to use every open year."
    )
    preview_plan_ids = fields.Many2many(
        'nhs.job.plan',
        string='Plans To Remind',
        compute='_compute_preview_plan_ids',
        help="The plans that will receive a reminder."
    )

    def _get_target_plans(self):
        """The job plans matching this wizard's target/year filters."""
        self.ensure_one()
        JobPlan = self.env['nhs.job.plan']
        domain = []
        if self.plan_year_id:
            domain.append(('plan_year_id', '=', self.plan_year_id.id))
        else:
            domain.append(('plan_year_id.state', '=', 'open'))
        if self.target == 'due':
            domain += [('state', 'not in', list(LOCKED_STATES) + ['superseded']),
                       ('review_due_date', '!=', False)]
        elif self.target == 'unsigned':
            domain += [('state', 'not in', list(LOCKED_STATES) + ['superseded'])]
        else:
            domain += [('state', 'in', ('proposed', 'in_discussion'))]
        return JobPlan.search(domain)

    @api.depends('target', 'plan_year_id')
    def _compute_preview_plan_ids(self):
        """Preview the plans this wizard will remind."""
        for wizard in self:
            wizard.preview_plan_ids = wizard._get_target_plans()

    def action_send_reminders(self):
        """Post a chatter reminder (and send the reminder template, when
        available) on every matched plan - the manual, on-demand counterpart
        to nhs.job.plan._cron_remind_plans_due()."""
        self.ensure_one()
        template = self.env.ref(
            'odoo_nhs_job_planning.mail_template_job_plan_reminder', raise_if_not_found=False)
        for plan in self._get_target_plans():
            plan.message_post(
                body="Reminder: this job plan needs attention (%s)." % dict(TARGETS).get(self.target))
            if template:
                template.send_mail(plan.id, force_send=False)
        return {'type': 'ir.actions.act_window_close'}
