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


class NhsDutyOfCandour(models.Model):
    _name = 'nhs.duty.of.candour'
    _description = 'Duty of Candour Compliance Record (CQC Reg 20)'
    _inherit = ['mail.thread']
    _order = 'written_deadline'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict',
                                  help='The incident that triggered this Duty of Candour obligation under CQC Regulation 20.')
    triggered_at = fields.Datetime(string='Triggered At', required=True,
                                   default=fields.Datetime.now, tracking=True,
                                   help='The date and time the Duty of Candour obligation was triggered. '
                                        'The 10-working-day written notification deadline is calculated from this point.')
    written_deadline = fields.Date(string='Written Notification Deadline',
                                   compute='_compute_written_deadline', store=True,
                                   help='+10 working days from trigger.')
    # Stage 1 — verbal
    verbal_done = fields.Boolean(string='Verbal Notification Done', tracking=True,
                                 help='Tick once the verbal notification has been given to the patient or their '
                                      'nominated person as required by CQC Regulation 20(2)(a).')
    verbal_at = fields.Datetime(string='Verbal Date/Time',
                                help='The date and time the verbal notification was given.')
    verbal_by_id = fields.Many2one('res.users', string='Verbal Notified By',
                                   help='The staff member who delivered the verbal notification.')
    verbal_notes = fields.Text(string='Verbal Notes',
                               help='Notes on the verbal notification — what was said, '
                                    'any questions asked, and the patient/family response.')
    # Stage 2 — written
    written_done = fields.Boolean(string='Written Notification Done', tracking=True,
                                  help='Tick once the written notification letter has been sent to the patient '
                                       'or their nominated person, as required by CQC Regulation 20(2)(b). '
                                       'Must be completed within 10 working days of the trigger.')
    written_at = fields.Datetime(string='Written Date/Time',
                                 help='The date and time the written notification was sent.')
    written_letter = fields.Binary(string='Signed Letter', attachment=True,
                                   help='Upload the signed Duty of Candour letter sent to '
                                        'the patient or their representative.')
    written_letter_filename = fields.Char(string='Signed Letter Filename')
    # Stage 3 — findings shared
    findings_shared_done = fields.Boolean(string='Findings Shared', tracking=True,
                                          help='Tick once the investigation findings and any resulting actions '
                                               'have been shared with the patient or their nominated person, '
                                               'as required by CQC Regulation 20(2)(c).')
    findings_shared_at = fields.Datetime(string='Findings Shared Date',
                                         help='The date and time investigation findings were shared with the patient.')
    # State
    state = fields.Selection([
        ('open', 'Open'),
        ('overdue', 'Overdue'),
        ('complete', 'Complete'),
    ], string='Status', compute='_compute_state', store=True, tracking=True,
       help='Open: obligation is in progress within deadline. '
            'Overdue: written notification deadline has passed without completion. '
            'Complete: all three stages done, or a valid exemption has been recorded.')
    exemption_reason = fields.Text(string='Exemption / Justification',
                                   help='Document lawful reason if contact cannot be made.')

    @api.depends('incident_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.incident_id:
                rec.display_name = f"DoC - {rec.incident_id.name}"
            else:
                rec.display_name = f"DoC #{rec.id or ''}"

    @api.depends('triggered_at')
    def _compute_written_deadline(self):
        Holiday = self.env['nhs.holiday']
        for rec in self:
            if rec.triggered_at:
                start = rec.triggered_at.date()
                rec.written_deadline = Holiday.add_working_days(start, 10)
            else:
                rec.written_deadline = False

    @api.depends('verbal_done', 'written_done', 'findings_shared_done',
                 'written_deadline', 'exemption_reason')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.exemption_reason or \
               (rec.verbal_done and rec.written_done and rec.findings_shared_done):
                rec.state = 'complete'
            elif rec.written_deadline and today > rec.written_deadline and not rec.written_done:
                rec.state = 'overdue'
            else:
                rec.state = 'open'

    def action_generate_letter(self):
        self.ensure_one()
        return self.env.ref(
            'odoo_nhs_incident_risk.action_report_doc_letter'
        ).report_action(self)

    @api.model
    def _cron_doc_deadlines(self):
        today = fields.Date.today()
        docs = self.search([('state', 'in', ['open', 'overdue'])])
        quality_group = self.env.ref(
            'odoo_nhs_incident_risk.group_hc_quality_lead', raise_if_not_found=False)
        quality_users = quality_group.users if quality_group else self.env['res.users']
        for doc in docs:
            if not doc.written_deadline or doc.written_done:
                continue
            days_left = (doc.written_deadline - today).days
            if days_left in (2, 5):
                for user in quality_users:
                    doc.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        note=f'DoC deadline in {days_left} days — {doc.incident_id.name}')
