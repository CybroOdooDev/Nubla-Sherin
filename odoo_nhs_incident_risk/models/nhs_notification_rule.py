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


class NhsNotificationRule(models.Model):
    _name = 'nhs.notification.rule'
    _description = 'Notification Rule (provider-type × category × harm → required notifications)'
    _order = 'provider_type, sequence'

    name = fields.Char(string='Rule Name', required=True,
                       help='A descriptive name for this rule (e.g. "NHS Trust — Moderate+ → LFPSE").')
    sequence = fields.Integer(default=10,
                              help='Determines the evaluation order. Lower numbers are processed first.')
    provider_type = fields.Selection([
        ('nhs_trust', 'NHS Trust'),
        ('gp_practice', 'GP Practice / PCN'),
        ('care_home', 'Care Home'),
        ('domiciliary_care', 'Domiciliary Care'),
        ('independent_hospital', 'Independent Hospital'),
        ('hospice', 'Hospice'),
        ('pharmacy', 'Pharmacy'),
        ('dental', 'Dental Practice'),
        ('all', 'All Provider Types'),
    ], string='Provider Type', required=True, default='all',
       help='The provider type this rule applies to. Select "All Provider Types" to apply universally.')
    category_id = fields.Many2one('nhs.incident.category', string='Category',
                                  help='Leave blank to match all categories. '
                                       'Set a category to restrict the rule to incidents of that type or its sub-categories.')
    min_harm_grade = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('death', 'Death'),
    ], string='Minimum Harm Grade',
       help='The rule only fires when the incident harm grade is at or above this level. '
            'Leave blank to match any harm grade.')
    require_cqc = fields.Boolean(string='Require CQC Notification',
                                 help='When ticked, a CQC statutory notification record will be automatically '
                                      'created on the incident if the rule conditions are met.')
    cqc_notification_type_id = fields.Many2one('nhs.cqc.notification.type',
                                               string='CQC Notification Type',
                                               help='The specific CQC notification type to create (e.g. Regulation 18 — Death).')
    require_lfpse = fields.Boolean(string='Require LFPSE Submission',
                                   help='When ticked, the incident LFPSE status is automatically set to "Pending" '
                                        'so it is included in the next LFPSE export batch.')
    suggest_riddor = fields.Boolean(string='Suggest RIDDOR Check',
                                    help='When ticked, the RIDDOR Check button is surfaced on the incident form '
                                         'to prompt the handler to run the determination wizard.')
    require_safeguarding = fields.Boolean(string='Require Safeguarding Flag',
                                          help='When ticked, the safeguarding concern flag is automatically set on '
                                               'the incident, restricting access to Safeguarding Officers.')
    deadline_days = fields.Integer(string='Deadline (days)',
                                   help='Number of calendar days from the incident report date within which '
                                        'the triggered notification or response must be completed.')
    active = fields.Boolean(default=True,
                            help='Untick to disable this rule without deleting it.')

    _HARM_ORDER = ['no_harm', 'low', 'moderate', 'severe', 'death']

    def _matches(self, incident):
        self.ensure_one()
        company_ptype = incident.company_id.provider_type or 'nhs_trust'
        if self.provider_type not in ('all', company_ptype):
            return False
        if self.category_id and self.category_id != incident.category_id:
            if not incident.category_id or \
               not incident.category_id.parent_path or \
               str(self.category_id.id) + '/' not in incident.category_id.parent_path:
                return False
        if self.min_harm_grade and incident.harm_grade:
            if self._HARM_ORDER.index(incident.harm_grade) < \
               self._HARM_ORDER.index(self.min_harm_grade):
                return False
        return True

    @api.model
    def evaluate(self, incident):
        """Apply all matching rules to the incident. Idempotent."""
        for rule in self.search([('active', '=', True)]):
            if not rule._matches(incident):
                continue
            if rule.require_lfpse and incident.lfpse_state == 'not_required':
                incident.with_context(nhs_workflow=True).write({'lfpse_state': 'pending'})
            if rule.require_safeguarding:
                incident.with_context(nhs_workflow=True).write({'safeguarding_flag': True})
            if rule.require_cqc and rule.cqc_notification_type_id:
                existing = incident.cqc_notification_ids.filtered(
                    lambda n: n.notification_type_id == rule.cqc_notification_type_id)
                if not existing:
                    self.env['nhs.cqc.notification'].create({
                        'incident_id': incident.id,
                        'notification_type_id': rule.cqc_notification_type_id.id,
                        'state': 'required',
                    })
            if rule.suggest_riddor and not incident.riddor_id:
                incident.with_context(nhs_workflow=True).write({'riddor_hint': True})
