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
from datetime import timedelta
from odoo import api, fields, models

class NHSESCondition(models.Model):
    _name = 'nhs.estate.condition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Six Facet Condition Survey'
    _order = 'survey_date desc, name'

    name = fields.Char(
        string='Survey Reference',
        required=True,
        default=lambda self: 'New Survey',
        help="Unique reference identifier for the survey (auto-generates 'New Survey' by default)"
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        required=True,
        ondelete='cascade',
        help="The building being surveyed"
    )
    space_id = fields.Many2one(
        'nhs.estate.space',
        string='Space (optional)',
        domain="[('building_id', '=', building_id)]",
        ondelete='cascade',
        help="Specific space or room being surveyed (optional for building-level surveys)"
    )
    survey_date = fields.Date(
        string='Survey Date',
        required=True,
        default=fields.Date.today,
        help="Date when the survey was conducted (defaults to today)"
    )
    surveyor_id = fields.Many2one(
        'res.users',
        string='Surveyor',
        help="User/person who conducted the survey"
    )
    facet_physical = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Physical Condition',
        help="Rating of the physical condition and structural integrity of the asset")
    facet_statutory = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Statutory/Safety Condition',
        help="Rating of compliance with statutory and safety regulations")
    facet_functional = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Functional Suitability',
        help="Rating of how well the asset meets its intended functional requirements")
    facet_utilisation = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Space Utilisation',
        help="Rating of how effectively the space is being utilised")
    facet_quality = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Quality/Environment',
        help="Rating of internal environmental quality and overall finish standards")
    facet_energy = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Energy Performance',
        help="Rating of energy efficiency and sustainability performance")
    overall_grade = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Overall Grade',
        compute='_compute_overall_grade',
        store=True,
        help="Overall condition grade automatically calculated from facet ratings")
    notes = fields.Text(
        string='Surveyor Notes',
        help="Additional observations, recommendations, and detailed findings from the survey"
    )
    next_survey_date = fields.Date(
        string='Next Survey Due',
        default=lambda self: fields.Date.today() + timedelta(days=30),
        help="Recommended date for the next survey based on findings and asset criticality"
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Photo Evidence',
        help="Supporting photographs and documentation attached as evidence to the survey"
    )

    @api.depends(
        'facet_physical', 'facet_statutory', 'facet_functional',
        'facet_utilisation', 'facet_quality', 'facet_energy'
    )
    def _compute_overall_grade(self):
        """Compute the overall grade for the condition survey.
        Retrieves the rollup method from settings ('worst' or 'weighted').
        - 'worst': Selects the worst grade (highest numeric penalty: D > C > B > A) across all facets.
        - 'weighted': Calculates the average of all filled facets, rounding to the nearest grade.
        """
        grade_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        rollup_method = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate.condition_rollup', 'worst'
        )
        for record in self:
            grades = []
            facet_values = {}
            if record.facet_physical:
                grades.append(record.facet_physical)
                facet_values['physical'] = record.facet_physical
            if record.facet_statutory:
                grades.append(record.facet_statutory)
                facet_values['statutory'] = record.facet_statutory
            if record.facet_functional:
                grades.append(record.facet_functional)
                facet_values['functional'] = record.facet_functional
            if record.facet_utilisation:
                grades.append(record.facet_utilisation)
                facet_values['utilisation'] = record.facet_utilisation
            if record.facet_quality:
                grades.append(record.facet_quality)
                facet_values['quality'] = record.facet_quality
            if record.facet_energy:
                grades.append(record.facet_energy)
                facet_values['energy'] = record.facet_energy
            if not grades:
                record.overall_grade = False
                continue
            if rollup_method == 'worst':
                worst_grade = max(grades, key=lambda x: grade_order.get(x, 0))
                record.overall_grade = worst_grade
            else:
                total_weight = len(facet_values)
                weighted_sum = sum(grade_order.get(grade, 0) for grade in facet_values.values())
                if total_weight > 0:
                    avg_numeric = weighted_sum / total_weight
                    if avg_numeric <= 1.5:
                        record.overall_grade = 'A'
                    elif avg_numeric <= 2.5:
                        record.overall_grade = 'B'
                    elif avg_numeric <= 3.5:
                        record.overall_grade = 'C'
                    else:
                        record.overall_grade = 'D'
                else:
                    record.overall_grade = False

    @api.onchange('survey_date')
    def _onchange_survey_date(self):
        """Update the next survey due date automatically when the survey date changes.
        Sets the default next survey date to 30 days after the selected survey date.
        """
        if self.survey_date:
            self.next_survey_date = self.survey_date + timedelta(days=30)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle sequence generation and trigger building grade recomputation.
        Args:
            vals_list (list of dicts): Value dicts for record creation.
        Returns:
            recordset: Newly created condition survey records.
        """
        # Set name for each record if not provided
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New Survey':
                vals['name'] = self.env['ir.sequence'].next_by_code('nhs.estate.condition') or 'New Survey'
        records = super().create(vals_list)
        buildings = records.mapped('building_id')
        for building in buildings:
            building._compute_latest_condition_grade()
        return records

    def write(self, vals):
        """Override write to recalculate building latest grade if survey dates or grades are updated.
        Args:
            vals (dict): Fields and values to update.
        Returns:
            bool: True if write succeeded, False otherwise.
        """
        affected_buildings = self.mapped('building_id')
        condition_fields = [
            'survey_date', 'overall_grade', 'facet_physical', 'facet_statutory',
            'facet_functional', 'facet_utilisation', 'facet_quality', 'facet_energy'
        ]
        res = super().write(vals)
        if any(field in vals for field in condition_fields):
            if 'building_id' in vals:
                old_buildings = self.browse(self.ids).mapped('building_id')
                affected_buildings |= old_buildings
            for building in affected_buildings:
                if building.exists():
                    building._compute_latest_condition_grade()
        return res

    def unlink(self):
        """Override unlink to trigger building latest grade recomputation upon survey deletion.
        Returns:
            bool: True if delete succeeded, False otherwise.
        """
        affected_buildings = self.mapped('building_id')
        res = super().unlink()
        for building in affected_buildings:
            if building.exists():
                building._compute_latest_condition_grade()
        return res

    def action_view_buildings(self):
        """Return an action displaying the detail form view of the associated building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Building',
            'res_model': 'nhs.estate.building',
            'view_mode': 'form',
            'res_id': self.building_id.id,
            'target': 'current',
        }

    def action_view_documents(self):
        """Return an action displaying all attachments/documents linked to this survey.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.condition'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.condition',
                'default_res_id': self.id,
            }
        }

    @api.model
    def cron_create_survey_reminders(self):
        """Cron job to automatically create reminders for surveys scheduled in the next 15-30 days.
        Identifies active surveys whose next survey due date falls within the upcoming
        15-30 day window, and schedules a standard task activity for each, avoiding duplicates.
        Returns:
            bool: True upon successful batch activity generation.
        """
        today = fields.Date.today()
        start_date = today + timedelta(days=15)
        end_date = today + timedelta(days=30)
        surveys = self.search([
            ('next_survey_date', '!=', False),
            ('next_survey_date', '>=', start_date),
            ('next_survey_date', '<=', end_date)
        ])
        for survey in surveys:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.estate.condition'),
                ('res_id', '=', survey.id),
                ('note', 'ilike', 'Survey Due Reminder'),
            ], limit=1)
            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if not activity_type:
                    activity_type = self.env['mail.activity.type'].search([], limit=1)
                if activity_type:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get_id('nhs.estate.condition'),
                        'res_id': survey.id,
                        'activity_type_id': activity_type.id,
                        'summary': f'📋 Survey Due: {survey.building_id.name}',
                        'note': f'Next survey due for {survey.building_id.name} on {survey.next_survey_date}',
                        'date_deadline': survey.next_survey_date - timedelta(days=10),
                        'user_id': survey.surveyor_id.id or survey.create_uid.id or self.env.user.id,
                    })
        return True

    @api.model
    def cron_check_overdue_surveys(self):
        """Cron job to scan for and alert on overdue condition surveys.
        Identifies surveys whose next survey due date is in the past, and creates
        an urgent mail activity reminder if one does not already exist.
        Returns:
            bool: True upon successful validation and execution.
        """
        today = fields.Date.today()
        overdue_surveys = self.search([
            ('next_survey_date', '!=', False),
            ('next_survey_date', '<', today)
        ])
        for survey in overdue_surveys:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.estate.condition'),
                ('res_id', '=', survey.id),
                ('note', 'ilike', 'OVERDUE Survey'),
            ], limit=1)
            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if not activity_type:
                    activity_type = self.env['mail.activity.type'].search([], limit=1)
                if activity_type:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get_id('nhs.estate.condition'),
                        'res_id': survey.id,
                        'activity_type_id': activity_type.id,
                        'summary': f'⚠️ OVERDUE Survey: {survey.building_id.name}',
                        'note': f'SURVEY OVERDUE! Next survey was due on {survey.next_survey_date}',
                        'date_deadline': today,
                        'user_id': survey.surveyor_id.id or survey.create_uid.id or self.env.user.id,
                    })
        return True
