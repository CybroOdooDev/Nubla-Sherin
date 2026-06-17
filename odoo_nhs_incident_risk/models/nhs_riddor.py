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
from datetime import timedelta


class NhsRiddor(models.Model):
    _name = 'nhs.riddor'
    _description = 'RIDDOR Determination & HSE Report Log'
    _order = 'id desc'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict',
                                  help='The incident this RIDDOR determination was carried out for.')
    person_id = fields.Many2one('nhs.incident.person', string='Injured Person',
                                help='The specific person from the incident record whose injury '
                                     'triggered the RIDDOR assessment.')
    reportable = fields.Boolean(string='Reportable to HSE', required=True,
                                help='Set automatically by the RIDDOR determination wizard. '
                                     'When True, a report must be submitted to the HSE within the statutory deadline.')
    riddor_category = fields.Selection([
        ('death', 'Death'),
        ('specified_injury', 'Specified Injury'),
        ('over_7_day', 'Over-7-Day Incapacitation'),
        ('occupational_disease', 'Occupational Disease'),
        ('dangerous_occurrence', 'Dangerous Occurrence'),
        ('gas', 'Gas Incident'),
    ], string='RIDDOR Category',
       help='The RIDDOR reporting category determined by the wizard: '
            'Death (10-day deadline), Specified Injury (10 days), '
            'Over-7-Day Incapacitation (15 days), Occupational Disease, Dangerous Occurrence, or Gas Incident.')
    determination_log = fields.Text(string='Determination Log',
                                    default='Manually created (no wizard transcript).',
                                    help='Full Q&A transcript of the wizard — audit defence.')
    report_deadline = fields.Date(string='HSE Report Deadline',
                                  compute='_compute_deadline', store=True,
                                  help='Auto-calculated statutory deadline for submitting the HSE report: '
                                       '10 days from incident date for death or specified injury; '
                                       '15 days for over-7-day incapacitation.')
    submitted = fields.Boolean(string='Submitted to HSE',
                               help='Tick once the RIDDOR report has been submitted to the HSE online portal '
                                    'at riddor.hse.gov.uk.')
    submitted_at = fields.Datetime(string='Submitted At',
                                   help='The date and time this RIDDOR report was submitted to the HSE.')
    hse_reference = fields.Char(string='HSE Reference (F2508)',
                                help='The reference number issued by the HSE upon receipt of the F2508 '
                                     'report. Record this for audit and insurance purposes.')

    @api.depends('incident_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.incident_id:
                rec.display_name = f"RIDDOR - {rec.incident_id.name}"
            else:
                rec.display_name = f"RIDDOR #{rec.id or ''}"

    @api.depends('riddor_category', 'incident_id.occurred_at')
    def _compute_deadline(self):
        for rec in self:
            if not rec.riddor_category or not rec.incident_id.occurred_at:
                rec.report_deadline = False
                continue
            base = rec.incident_id.occurred_at.date()
            if rec.riddor_category in ('death', 'specified_injury'):
                rec.report_deadline = base + timedelta(days=10)
            elif rec.riddor_category == 'over_7_day':
                rec.report_deadline = base + timedelta(days=15)
            else:
                rec.report_deadline = base + timedelta(days=10)
