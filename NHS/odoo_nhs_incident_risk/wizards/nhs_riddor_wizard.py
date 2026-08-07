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


class NhsRiddorWizard(models.TransientModel):
    """Wizard that walks through the RIDDOR decision tree to determine reportability."""
    _name = 'nhs.riddor.wizard'
    _description = 'RIDDOR Determination Wizard'

    incident_id = fields.Many2one('nhs.incident', string='Incident', required=True,
                                  help='The incident being assessed for RIDDOR reportability.')
    person_id = fields.Many2one('nhs.incident.person', string='Injured Person',
                                help='The specific person from the incident record whose injury is being assessed. '
                                     'Leave blank if the assessment relates to a dangerous occurrence with no identified injured person.')

    # Q1
    anyone_injured = fields.Boolean(string='Was anyone injured or became ill as a result?',
                                    help='Answer Yes if any person — worker, patient, visitor, or contractor — '
                                         'suffered a physical injury or illness as a direct result of the incident.')
    # Q2
    worker_injured = fields.Boolean(string='Is the injured person a worker (employee/self-employed)?',
                                    help='A "worker" under RIDDOR includes employees, self-employed contractors, '
                                         'apprentices, and trainees working on your premises. '
                                         'Patients, residents, and visitors are NOT workers.')
    # Q3
    fatal = fields.Boolean(string='Did the injury result in death?',
                           help='Answer Yes if the injured worker died as a result of the work-related injury or illness. '
                                'Death of a worker must be reported immediately by phone and then within 10 days via F2508.')
    # Q4 — specified injuries
    specified_fracture = fields.Boolean(string='Fracture (other than finger/thumb/toe)?',
                                        help='Includes fractures of the skull, spine, pelvis, arm, wrist, leg, ankle, '
                                             'or collarbone. Fractures of fingers, thumbs, or toes are NOT specified injuries.')
    specified_amputation = fields.Boolean(string='Amputation?',
                                          help='Loss of a limb or part of a limb, including a finger, thumb, or toe.')
    specified_sight = fields.Boolean(string='Loss or reduction of sight?',
                                     help='Includes permanent loss of sight in one or both eyes, or any reduction '
                                          'in visual acuity requiring treatment.')
    specified_crush = fields.Boolean(string='Crush injury causing damage to brain or internal organs?',
                                     help='Answer Yes if the injury involved crushing that resulted in damage to '
                                          'the brain or internal organs in the chest or abdomen.')
    specified_burn = fields.Boolean(string='Burn covering more than 10% of body or eyes/breathing?',
                                    help='Includes chemical or hot metal burns covering more than 10% of the body surface, '
                                         'or burns affecting the eyes or any part of the respiratory tract.')
    specified_scalp = fields.Boolean(string='Scalping?',
                                     help='Separation of skin from the head due to a traumatic injury.')
    specified_unconscious = fields.Boolean(string='Loss of consciousness from head injury or asphyxia?',
                                           help='Answer Yes if the injured person lost consciousness as a direct result '
                                                'of a head injury or through asphyxia (lack of oxygen).')
    specified_enclosed_space = fields.Boolean(string='Requiring resuscitation or admission 24h+ from enclosed space?',
                                              help='Answer Yes if the worker required resuscitation or was kept in hospital '
                                                   'for more than 24 hours following an injury from working in an enclosed space.')
    # Q5
    over_7_day = fields.Boolean(string='Incapacitated from usual work for more than 7 consecutive days (excluding day of accident)?',
                                help='Answer Yes if the injured worker was unable to perform their normal work duties '
                                     'for more than 7 consecutive days after the accident (not counting the day of the accident). '
                                     'This type must be reported within 15 days of the accident.')
    # Q6
    dangerous_occurrence = fields.Boolean(string='Did a dangerous occurrence happen (collapse, explosion, escape of substance, etc.)?',
                                          help='Dangerous occurrences are defined events that must be reported even if no-one is hurt, '
                                               'such as the collapse of a scaffold, an explosion, an uncontrolled release of a '
                                               'biological agent, or a train collision. See RIDDOR Schedule 2 for the full list.')
    # Q7
    occupational_disease = fields.Boolean(string='Has a doctor diagnosed an occupational disease?',
                                          help='Answer Yes if a doctor has confirmed a diagnosis of a reportable occupational disease '
                                               '(e.g. carpal tunnel syndrome, occupational dermatitis, Hand-Arm Vibration Syndrome) '
                                               'and the worker performs work that could have caused it. See RIDDOR Schedule 3.')

    # Outcome (computed)
    reportable = fields.Boolean(string='Reportable to HSE', compute='_compute_outcome',
                                help='Auto-calculated from the answers above. '
                                     'When True, a report must be submitted to the HSE within the statutory deadline.')
    riddor_category = fields.Selection([
        ('death', 'Death'),
        ('specified_injury', 'Specified Injury'),
        ('over_7_day', 'Over-7-Day Incapacitation'),
        ('occupational_disease', 'Occupational Disease'),
        ('dangerous_occurrence', 'Dangerous Occurrence'),
    ], string='RIDDOR Category', compute='_compute_outcome',
       help='The RIDDOR category auto-determined from the wizard answers. '
            'Drives the statutory reporting deadline: 10 days for death/specified injury, '
            '15 days for over-7-day incapacitation.')

    @api.depends('anyone_injured', 'worker_injured', 'fatal',
                 'specified_fracture', 'specified_amputation', 'specified_sight',
                 'specified_crush', 'specified_burn', 'specified_scalp',
                 'specified_unconscious', 'specified_enclosed_space',
                 'over_7_day', 'dangerous_occurrence', 'occupational_disease')
    def _compute_outcome(self):
        """Derive RIDDOR reportability and category from the answers, in priority order:
        death, then specified injury, over-7-day incapacitation, occupational disease,
        and dangerous occurrence."""
        for rec in self:
            if rec.fatal:
                rec.reportable = True
                rec.riddor_category = 'death'
            elif any([rec.specified_fracture, rec.specified_amputation,
                      rec.specified_sight, rec.specified_crush, rec.specified_burn,
                      rec.specified_scalp, rec.specified_unconscious,
                      rec.specified_enclosed_space]) and rec.anyone_injured:
                rec.reportable = True
                rec.riddor_category = 'specified_injury'
            elif rec.over_7_day and rec.worker_injured:
                rec.reportable = True
                rec.riddor_category = 'over_7_day'
            elif rec.occupational_disease:
                rec.reportable = True
                rec.riddor_category = 'occupational_disease'
            elif rec.dangerous_occurrence:
                rec.reportable = True
                rec.riddor_category = 'dangerous_occurrence'
            else:
                rec.reportable = False
                rec.riddor_category = False

    def _build_log(self):
        """Render the wizard's answers and outcome as a plain-text determination log."""
        lines = ['RIDDOR DETERMINATION LOG', '=' * 40]
        lines.append(f'Incident: {self.incident_id.name}')
        lines.append(f'Anyone injured: {self.anyone_injured}')
        lines.append(f'Worker: {self.worker_injured}')
        lines.append(f'Fatal: {self.fatal}')
        lines.append(f'Specified injury — fracture: {self.specified_fracture}')
        lines.append(f'Specified injury — amputation: {self.specified_amputation}')
        lines.append(f'Specified injury — sight: {self.specified_sight}')
        lines.append(f'Specified injury — crush: {self.specified_crush}')
        lines.append(f'Specified injury — burn: {self.specified_burn}')
        lines.append(f'Specified injury — scalp: {self.specified_scalp}')
        lines.append(f'Specified injury — unconscious: {self.specified_unconscious}')
        lines.append(f'Specified injury — enclosed space: {self.specified_enclosed_space}')
        lines.append(f'Over-7-day incapacitation: {self.over_7_day}')
        lines.append(f'Dangerous occurrence: {self.dangerous_occurrence}')
        lines.append(f'Occupational disease: {self.occupational_disease}')
        lines.append('=' * 40)
        lines.append(f'OUTCOME: Reportable = {self.reportable}')
        if self.riddor_category:
            lines.append(f'Category: {self.riddor_category}')
        return '\n'.join(lines)

    def action_confirm(self):
        """Create the nhs.riddor record from the determination, link it to the
        incident, and open the new record's form view."""
        self.ensure_one()
        log = self._build_log()
        riddor = self.env['nhs.riddor'].create({
            'incident_id': self.incident_id.id,
            'person_id': self.person_id.id if self.person_id else False,
            'reportable': self.reportable,
            'riddor_category': self.riddor_category or False,
            'determination_log': log,
        })
        self.incident_id.with_context(nhs_workflow=True).write({
            'riddor_id': riddor.id,
            'riddor_hint': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'RIDDOR Record',
            'res_model': 'nhs.riddor',
            'res_id': riddor.id,
            'view_mode': 'form',
            'target': 'current',
        }
