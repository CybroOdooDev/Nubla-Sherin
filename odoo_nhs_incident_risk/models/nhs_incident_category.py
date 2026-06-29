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


class NhsIncidentCategory(models.Model):
    _name = 'nhs.incident.category'
    _description = 'Incident Category (two-level tree)'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True,
                       help='The category name shown on incident forms and in reports.')
    parent_id = fields.Many2one('nhs.incident.category', string='Parent Category',
                                index=True, ondelete='restrict',
                                help='The top-level category this sub-category belongs to. '
                                     'Categories support a maximum of two levels.')
    parent_path = fields.Char(index=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True, recursive=True,
                                help='Auto-computed full path including the parent category name.')
    provider_type_ids = fields.Many2many(
        'nhs.provider.type',
        'nhs_incident_category_provider_type_rel',
        'category_id', 'provider_type_id',
        string='Provider Types',
        help='Provider types this category applies to. Leave empty = universal (all types).')
    default_response_level = fields.Selection([
        ('none', 'No separate response'),
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'Patient Safety Incident Investigation (PSII)'),
    ], string='Default PSIRF Response',
       help='When an incident is assigned to this category, this response level is automatically suggested. '
            'The handler may override it during triage.')
    default_harm_floor = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('death', 'Death'),
    ], string='Minimum Harm Suggestion',
       help='When an incident is assigned to this category, this harm grade is automatically suggested '
            'as the minimum. The handler may set a higher grade during triage.')
    riddor_hint = fields.Boolean(string='Show RIDDOR Prompt',
                                 help='Auto-surface the RIDDOR wizard for incidents in this category.')
    cqc_notification_type_ids = fields.Many2many(
        'nhs.cqc.notification.type',
        string='CQC Notification Types')
    active = fields.Boolean(default=True,
                            help='Untick to archive this category. Archived categories are hidden from '
                                 'incident forms but can be restored.')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f'{rec.parent_id.complete_name} / {rec.name}'
            else:
                rec.complete_name = rec.name

    @api.constrains('parent_id')
    def _check_depth(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id:
                raise ValidationError('Incident categories support a maximum of 2 levels.')

    def name_get(self):
        return [(r.id, r.complete_name) for r in self]
