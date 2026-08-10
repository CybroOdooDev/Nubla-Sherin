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


class NhsCqcNotificationType(models.Model):
    _name = 'nhs.cqc.notification.type'
    _description = 'CQC Statutory Notification Type'
    _order = 'name'

    name = fields.Char(string='Notification Type', required=True,
                       help='The name of this CQC statutory notification type (e.g. "Death of a service user", '
                            '"Deprivation of liberty", "Abuse or allegations of abuse").')
    statutory_basis = fields.Char(string='Statutory Basis',
                                  help='e.g. Regulation 16, 17, or 18')
    description = fields.Text(string='Description',
                               help='Further detail on what triggers this notification type and '
                                    'the applicable CQC guidance or provider handbook reference.')
    active = fields.Boolean(default=True,
                            help='Untick to retire this notification type. Existing notifications are retained.')


class NhsCqcNotification(models.Model):
    _name = 'nhs.cqc.notification'
    _description = 'CQC Statutory Notification Record'
    _inherit = ['mail.thread']
    _order = 'id desc'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict',
                                  help='The incident this CQC notification relates to.')
    notification_type_id = fields.Many2one('nhs.cqc.notification.type',
                                           string='Notification Type', required=True,
                                           help='The specific CQC statutory notification type required '
                                                '(e.g. Death of a service user — Regulation 16).')
    statutory_basis = fields.Char(related='notification_type_id.statutory_basis',
                                  string='Statutory Basis', readonly=True,
                                  help='The legal regulation underpinning this notification obligation, '
                                       'auto-populated from the notification type.')
    state = fields.Selection([
        ('required', 'Required'),
        ('submitted', 'Submitted'),
        ('not_required', 'Not Required'),
    ], string='Status', required=True, default='required', tracking=True,
       help='Required: notification must be submitted to CQC. '
            'Submitted: notification has been sent and the CQC reference recorded. '
            'Not Required: a determination has been made that this notification does not apply — '
            'a justification must be provided.')
    justification = fields.Text(string='Justification',
                                help='Required when state = Not Required.')
    submitted_at = fields.Datetime(string='Submitted At',
                                   help='The date and time this notification was formally submitted to the CQC.')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By',
                                      help='The staff member who submitted this notification to the CQC.')
    cqc_reference = fields.Char(string='CQC Reference',
                                help='The reference number issued by the CQC upon receipt of this notification. '
                                     'Record this for audit and traceability purposes.')

    def action_submit(self):
        for rec in self:
            vals = {'state': 'submitted'}
            if not rec.submitted_at:
                vals['submitted_at'] = fields.Datetime.now()
            if not rec.submitted_by_id:
                vals['submitted_by_id'] = self.env.user.id
            rec.write(vals)

    def action_not_required(self):
        self.write({'state': 'not_required'})

    def action_required(self):
        self.write({
            'state': 'required',
            'submitted_at': False,
            'submitted_by_id': False,
            'cqc_reference': False,
            'justification': False,
        })

    @api.depends('incident_id.name', 'notification_type_id.name')
    def _compute_display_name(self):
        for rec in self:
            incident_name = rec.incident_id.name or 'New'
            notif_type = rec.notification_type_id.name or ''
            if notif_type:
                rec.display_name = f"{incident_name} - {notif_type}"
            else:
                rec.display_name = f"CQC Notification for {incident_name}"
