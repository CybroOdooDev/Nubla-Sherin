from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsTriageWizard(models.TransientModel):
    _name = 'nhs.triage.wizard'
    _description = 'Incident Triage Wizard'

    incident_id = fields.Many2one('nhs.incident', string='Incident', required=True)
    category_id = fields.Many2one('nhs.incident.category', string='Category',
                                  required=True)
    location_id = fields.Many2one('nhs.location', string='Location', required=True)
    harm_grade = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low Harm'),
        ('moderate', 'Moderate Harm'),
        ('severe', 'Severe Harm'),
        ('death', 'Death'),
    ], string='NPSA Harm Grade', required=True)
    physical_harm = fields.Selection([
        ('none', 'None'), ('low', 'Low'), ('moderate', 'Moderate'),
        ('severe', 'Severe'), ('fatal', 'Fatal'),
    ], string='Physical Harm (LFPSE)')
    psychological_harm = fields.Selection([
        ('none', 'None'), ('low', 'Low'), ('moderate', 'Moderate'), ('severe', 'Severe'),
    ], string='Psychological Harm (LFPSE)')
    response_level = fields.Selection([
        ('none', 'No Separate Response'),
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'PSII'),
    ], string='PSIRF Response Level', required=True)
    decision = fields.Selection([
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('duplicate', 'Mark as Duplicate'),
    ], string='Decision', required=True, default='accept')
    rejection_reason = fields.Text(string='Rejection Reason')
    duplicate_of_id = fields.Many2one('nhs.incident', string='Duplicate Of')
    handler_id = fields.Many2one('res.users', string='Assign Handler')

    @api.onchange('incident_id')
    def _onchange_incident(self):
        if self.incident_id:
            self.category_id = self.incident_id.category_id
            self.location_id = self.incident_id.location_id
            self.response_level = self.incident_id.response_level or 'none'

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id and self.category_id.default_response_level:
            self.response_level = self.category_id.default_response_level

    def action_confirm(self):
        self.ensure_one()
        inc = self.incident_id
        if self.decision == 'reject':
            if not self.rejection_reason:
                raise UserError('Rejection reason is required.')
            inc.action_reject(self.rejection_reason)
        elif self.decision == 'duplicate':
            if not self.duplicate_of_id:
                raise UserError('Please specify the master incident.')
            inc.action_mark_duplicate(self.duplicate_of_id.id)
        else:
            inc.with_context(nhs_workflow=True).write({
                'category_id': self.category_id.id,
                'location_id': self.location_id.id,
                'harm_grade': self.harm_grade,
                'physical_harm': self.physical_harm,
                'psychological_harm': self.psychological_harm,
                'response_level': self.response_level,
            })
            if self.handler_id:
                inc.with_context(nhs_workflow=True).write(
                    {'handler_id': self.handler_id.id})
            inc.with_context(nhs_workflow=True).write({'state': 'triage'})
            self.env['nhs.notification.rule'].evaluate(inc)
        return {'type': 'ir.actions.act_window_close'}
