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
from odoo.exceptions import ValidationError

class NHSComplianceRemedial(models.Model):
    """Model representing remedial actions raised to correct compliance failures."""
    _name = 'nhs.compliance.remedial'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Remedial Action'
    _order = 'due_date, priority desc'

    name = fields.Char(string='Name', required=True,
                       help='A short, descriptive title for this remedial action (e.g. Replace corroded pipe section).')
    item_id = fields.Many2one('nhs.compliance.item', string='Compliance Item', required=True,
                              domain="[('status', 'in', ['failed'])]",
                              help='The compliance item that requires this remedial action.')
    test_id = fields.Many2one(
        'nhs.compliance.test', string='Originating Test',
        domain="[('item_id', '=', item_id), ('outcome', 'in', ['fail', 'remedial_required'])]",
        help='The failed or remedial-required test record that triggered this action.'
    )
    description = fields.Text(string='Description',
                              help='Detailed description of the deficiency found and the corrective work required.')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='medium',
       help='The urgency of this remedial action; Urgent items must be addressed immediately.')
    risk_rating = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Risk Rating', default='medium',
       help='The assessed risk level if this remedial action is not completed.')
    owner_id = fields.Many2one('res.users', string='Owner', required=True,
                               help='The person responsible for completing this remedial action.')
    due_date = fields.Date(string='Due Date', required=True,
                           help='The date by which this remedial action must be completed.')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('awaiting_parts', 'Awaiting Parts'),
        ('completed', 'Completed'),
        ('verified', 'Verified')
    ], string='State', default='open', required=True,
       help='Current workflow state of the remedial action.')
    completion_evidence = fields.Text(string='Completion Evidence',
                                help='Description of the evidence confirming that the remedial work has been completed '
                                     '(e.g. inspection photos, contractor report reference).')
    verified_by_id = fields.Many2one('res.users', string='Verified By',
                help='The person who independently verified that the remedial action was completed satisfactorily.')
    verified_at = fields.Datetime(string='Verified At',
                                  help='The date and time at which the remedial action was formally verified.')
    backlog_ref = fields.Many2one('nhs.estate.backlog',string='Backlog Reference',
                               help='Optional link to an Estate Register backlog item')

    @api.constrains('state')
    def _check_completion_evidence(self):
        for remedial in self:
            if remedial.state == 'completed' and not remedial.completion_evidence:
                raise ValidationError('Completion evidence is required when marking as completed.')

    def action_start_progress(self):
        """Move the remedial action to the 'In Progress' state."""
        self.state = 'in_progress'

    def action_await_parts(self):
        """Move the remedial action to the 'Awaiting Parts' state."""
        self.state = 'awaiting_parts'

    def action_complete(self):
        """Mark the remedial action as completed (requires completion evidence)."""
        self.state = 'completed'

    def action_verify(self):
        """Mark the remedial action as verified, recording the verifier and timestamp."""
        self.state = 'verified'
        self.verified_by_id = self.env.user
        self.verified_at = fields.Datetime.now()

    def action_view_item(self):
        """Open the form view of the parent compliance item."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compliance Item',
            'res_model': 'nhs.compliance.item',
            'view_mode': 'form',
            'res_id': self.item_id.id,
            'target': 'current',
        }

    def action_view_test(self):
        """Open the form view of the originating compliance test."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compliance Test',
            'res_model': 'nhs.compliance.test',
            'view_mode': 'form',
            'res_id': self.test_id.id,
            'target': 'current',
        }

    @api.model
    def _check_overdue_remedials(self):
        """Scheduled action to detect overdue remedial actions and escalate them.
        For each open remedial action whose due date has passed, this method:
        - Posts an escalation alert in the parent compliance item's chatter.
        - Sends an email reminder to the responsible owner (and duty holder if
          the item is overdue beyond the configured escalation threshold).
        - Creates a to-do activity for the responsible person and, where
          applicable, the duty holder.
        """
        today = fields.Date.today()
        overdue_remedials = self.search([
            ('state', 'in', ['open', 'in_progress', 'awaiting_parts']),
            ('due_date', '<', today)
        ])
        escalation_threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_compliance.escalation_threshold', 7))
        template = self.env.ref('odoo_nhs_estate_compliance.mail_template_remedial_escalation',
                                raise_if_not_found=False)
        for remedial in overdue_remedials:
            item = remedial.item_id
            responsible_user = item.responsible_person_id or remedial.owner_id or self.env.user
            dh_domain = [('duty_role_id.code', '=', 'DH')]
            dh_assignment = self.env['nhs.duty.assignment']
            if item.site_id:
                dh_assignment = self.env['nhs.duty.assignment'].search(dh_domain + [('site_id', '=', item.site_id.id)],
                                                                       limit=1)
            if not dh_assignment and item.building_id:
                dh_assignment = self.env['nhs.duty.assignment'].search(dh_domain +
                                                                [('building_id', '=', item.building_id.id)], limit=1)
            if not dh_assignment:
                dh_assignment = self.env['nhs.duty.assignment'].search(dh_domain, limit=1)
            dh_user_id = dh_assignment.person_id.id if dh_assignment else False
            dh_email = dh_assignment.person_id.email if dh_assignment else False
            days_overdue = (today - remedial.due_date).days
            escalation_msg = (
                "ESCALATION ALERT: Remedial Action '%s' is OVERDUE by %s days (Due: %s). Assigned to: %s."
            ) % (remedial.name, days_overdue, remedial.due_date, remedial.owner_id.name)
            if days_overdue > escalation_threshold and dh_user_id:
                escalation_msg += " Escalated to Duty Holder."
            item.message_post(body=escalation_msg)
            if template:
                email_to = remedial.owner_id.email or responsible_user.email
                if days_overdue > escalation_threshold and dh_email:
                    email_to = f"{email_to},{dh_email}" if email_to else dh_email
                if email_to:
                    template.send_mail(remedial.id, email_values={'email_to': email_to}, force_send=True)
            existing_resp = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.compliance.item'),
                ('res_id', '=', item.id),
                ('user_id', '=', responsible_user.id),
                ('summary', '=', f"Overdue Remedial Action: {remedial.name}"),
            ])
            if not existing_resp:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id if activity_type else False,
                    'res_model_id': self.env['ir.model']._get_id('nhs.compliance.item'),
                    'res_id': item.id,
                    'user_id': responsible_user.id,
                    'summary': f"Overdue Remedial Action: {remedial.name}",
                    'note': f"The remedial action '{remedial.name}' is overdue since {remedial.due_date}. "
                            f"Owner: {remedial.owner_id.name}.",
                    'date_deadline': today,
                })
            if days_overdue > escalation_threshold and dh_user_id and dh_user_id != responsible_user.id:
                existing_dh = self.env['mail.activity'].search([
                    ('res_model', '=', 'nhs.compliance.item'),
                    ('res_id', '=', item.id),
                    ('user_id', '=', dh_user_id),
                    ('summary', '=', f"ESCALATION: Overdue Remedial: {remedial.name}"),
                ])
                if not existing_dh:
                    activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                    self.env['mail.activity'].create({
                        'activity_type_id': activity_type.id if activity_type else False,
                        'res_model_id': self.env['ir.model']._get_id('nhs.compliance.item'),
                        'res_id': item.id,
                        'user_id': dh_user_id,
                        'summary': f"ESCALATION: Overdue Remedial: {remedial.name}",
                        'note': f"ESCALATED REMEDIAL ACTION: '{remedial.name}' is overdue by {days_overdue} days. "
                                f"Owner: {remedial.owner_id.name}.",
                        'date_deadline': today,
                    })

    def write(self, vals):
        original_states = {}
        if 'state' in vals and vals.get('state') == 'verified':
            self.env.cr.execute(
                "SELECT id, state FROM nhs_compliance_remedial WHERE id IN %s",
                [tuple(self.ids)]
            )
            original_states = dict(self.env.cr.fetchall())
        res = super(NHSComplianceRemedial, self).write(vals)
        if 'state' in vals and vals.get('state') == 'verified':
            for remedial in self:
                if original_states.get(remedial.id) != 'verified':
                    item = remedial.item_id
                    if item:
                        open_remedials = item.remedial_ids.filtered(
                            lambda r: r.state not in ['completed', 'verified']
                        )
                        if not open_remedials:
                            item._sync_maintenance_records()
                            chatter_msg = (
                                "All remedial actions have been verified. "
                                "A re-test is required before the item can return to a compliant state."
                            )
                            item.message_post(body=chatter_msg)
                            responsible_user = item.responsible_person_id
                            if responsible_user:
                                summary = "Re-test required after remedial verification"
                                note = (
                                    "All remedials have been verified and a new compliance "
                                    "test must be recorded."
                                )
                                existing_activity = self.env['mail.activity'].search([
                                    ('res_model', '=', 'nhs.compliance.item'),
                                    ('res_id', '=', item.id),
                                    ('user_id', '=', responsible_user.id),
                                    ('summary', '=', summary),
                                ])
                                if not existing_activity:
                                    activity_type = self.env.ref('mail.mail_activity_data_todo',
                                                                 raise_if_not_found=False)
                                    self.env['mail.activity'].create({
                                        'activity_type_id': activity_type.id if activity_type else False,
                                        'res_model_id': self.env['ir.model']._get_id('nhs.compliance.item'),
                                        'res_id': item.id,
                                        'user_id': responsible_user.id,
                                        'summary': summary,
                                        'note': note,
                                        'date_deadline': fields.Date.today(),
                                    })
        return res
