from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NhsIncidentCategory(models.Model):
    _name = 'nhs.incident.category'
    _description = 'Incident Category (two-level tree)'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('nhs.incident.category', string='Parent Category',
                                index=True, ondelete='restrict')
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True)
    provider_types = fields.Char(
        string='Provider Types',
        help='Comma-separated provider_type keys. Leave empty for all types.')
    default_response_level = fields.Selection([
        ('none', 'No separate response'),
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'Patient Safety Incident Investigation (PSII)'),
    ], string='Default PSIRF Response')
    default_harm_floor = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('death', 'Death'),
    ], string='Minimum Harm Suggestion')
    riddor_hint = fields.Boolean(string='Show RIDDOR Prompt',
                                 help='Auto-surface the RIDDOR wizard for incidents in this category.')
    cqc_notification_type_ids = fields.Many2many(
        'nhs.cqc.notification.type',
        string='CQC Notification Types')
    active = fields.Boolean(default=True)

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
