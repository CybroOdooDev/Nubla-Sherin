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

TRAINING_CLASSES = [
    ('statutory', 'Statutory'),
    ('mandatory', 'Mandatory'),
    ('role_specific', 'Role-Specific'),
    ('local', 'Local'),
]


class NhsTrainingSubject(models.Model):
    _name = 'nhs.training.subject'
    _description = 'A statutory/mandatory training subject (optionally levelled)'
    _order = 'name, level'
    _rec_name = 'complete_name'

    name = fields.Char(
        string='Subject',
        required=True,
        help="Subject name (e.g. 'Safeguarding Children', 'Fire Safety')."
    )
    level = fields.Selection([
        ('Level 1', 'Level 1'),
        ('Level 2', 'Level 2'),
        ('Level 3', 'Level 3'),
        ('Level 4', 'Level 4'),
        ('Level 5', 'Level 5'),
    ],
        string='Level',
        help="Level where applicable (e.g. 'Level 1', 'Level 2', 'Level 3')."
             " Subject + level is the unique combination."
    )
    complete_name = fields.Char(
        string='Subject (Level)',
        compute='_compute_complete_name',
        store=True,
        help="Subject and level combined, e.g. 'Safeguarding Children (Level 3)'."
    )
    code = fields.Char(
        string='CSTF Code',
        help="CSTF reference/code for portability between organisations."
    )
    training_class = fields.Selection(
        TRAINING_CLASSES,
        string='Classification',
        required=True,
        default='mandatory',
        help="Statutory (required by law) / Mandatory (required by employer policy)"
             " / Role-Specific / Local (organisation-specific addition)."
    )
    default_frequency_months = fields.Integer(
        string='Default Refresh (Months)',
        help="Refresh interval in months (12 = annual, 36 = 3-yearly)."
             " Leave blank/0 for a one-off subject with no expiry."
    )
    is_one_off = fields.Boolean(
        string='One-Off (No Expiry)',
        help="True = never expires once completed (e.g. induction)."
    )
    default_lead_days = fields.Integer(
        string='Default Due-Soon Window (Days)',
        default=60,
        help="Default number of days before expiry at which a completion becomes 'due soon'."
    )
    cstf_aligned = fields.Boolean(
        string='CSTF Aligned',
        help="Whether this is one of the UK Core Skills Training Framework subjects."
    )
    requirement_count = fields.Integer(
        string='Requirement Count',
        compute='_compute_requirement_count',
        help="Requirements (profile/staff-group/individual) referencing this subject."
    )
    record_count = fields.Integer(
        string='Completion Count',
        compute='_compute_record_count',
        help="Completion records recorded against this subject."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable/disable this subject for the organisation."
    )

    _name_level_uniq = models.Constraint(
        'UNIQUE(name, level)',
        'A training subject with this name and level already exists!'
    )

    @api.depends('name', 'level')
    def _compute_complete_name(self):
        """Combine subject name and level into a single display name."""
        for subject in self:
            subject.complete_name = '%s (%s)' % (subject.name, subject.level) \
                if subject.level else subject.name

    @api.onchange('default_frequency_months')
    def _onchange_default_frequency_months(self):
        """Flag the subject as one-off whenever no refresh frequency is set."""
        for subject in self:
            subject.is_one_off = not subject.default_frequency_months

    def _compute_requirement_count(self):
        """Count requirements (profile/staff-group/individual) referencing each subject."""
        req_data = self.env['nhs.training.requirement']._read_group(
            [('subject_id', 'in', self.ids)],
            ['subject_id'], ['__count'],
        )
        counts = {subject.id: count for subject, count in req_data}
        for subject in self:
            subject.requirement_count = counts.get(subject.id, 0)

    def _compute_record_count(self):
        """Count completion records recorded against each subject."""
        rec_data = self.env['nhs.training.record']._read_group(
            [('subject_id', 'in', self.ids)],
            ['subject_id'], ['__count'],
        )
        counts = {subject.id: count for subject, count in rec_data}
        for subject in self:
            subject.record_count = counts.get(subject.id, 0)

    def action_view_requirements(self):
        """Open the requirements that reference this subject."""
        self.ensure_one()
        return {
            'name': 'Requirements',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.requirement',
            'view_mode': 'list,form',
            'domain': [('subject_id', '=', self.id)],
            'context': {'default_subject_id': self.id},
        }

    def action_view_records(self):
        """Open the completion records recorded against this subject."""
        self.ensure_one()
        return {
            'name': 'Completion Records',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.record',
            'view_mode': 'list,form',
            'domain': [('subject_id', '=', self.id)],
            'context': {'default_subject_id': self.id},
        }
