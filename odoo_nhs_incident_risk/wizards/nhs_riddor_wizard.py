from odoo import api, fields, models


class NhsRiddorWizard(models.TransientModel):
    _name = 'nhs.riddor.wizard'
    _description = 'RIDDOR Determination Wizard'

    incident_id = fields.Many2one('nhs.incident', string='Incident', required=True)
    person_id = fields.Many2one('nhs.incident.person', string='Injured Person')

    # Q1
    anyone_injured = fields.Boolean(string='Was anyone injured or became ill as a result?')
    # Q2
    worker_injured = fields.Boolean(string='Is the injured person a worker (employee/self-employed)?')
    # Q3
    fatal = fields.Boolean(string='Did the injury result in death?')
    # Q4 — specified injuries
    specified_fracture = fields.Boolean(string='Fracture (other than finger/thumb/toe)?')
    specified_amputation = fields.Boolean(string='Amputation?')
    specified_sight = fields.Boolean(string='Loss or reduction of sight?')
    specified_crush = fields.Boolean(string='Crush injury causing damage to brain or internal organs?')
    specified_burn = fields.Boolean(string='Burn covering more than 10% of body or eyes/breathing?')
    specified_scalp = fields.Boolean(string='Scalping?')
    specified_unconscious = fields.Boolean(string='Loss of consciousness from head injury or asphyxia?')
    specified_enclosed_space = fields.Boolean(string='Requiring resuscitation or admission 24h+ from enclosed space?')
    # Q5
    over_7_day = fields.Boolean(string='Incapacitated from usual work for more than 7 consecutive days (excluding day of accident)?')
    # Q6
    dangerous_occurrence = fields.Boolean(string='Did a dangerous occurrence happen (collapse, explosion, escape of substance, etc.)?')
    # Q7
    occupational_disease = fields.Boolean(string='Has a doctor diagnosed an occupational disease?')

    # Outcome (computed)
    reportable = fields.Boolean(string='Reportable to HSE', compute='_compute_outcome')
    riddor_category = fields.Selection([
        ('death', 'Death'),
        ('specified_injury', 'Specified Injury'),
        ('over_7_day', 'Over-7-Day Incapacitation'),
        ('occupational_disease', 'Occupational Disease'),
        ('dangerous_occurrence', 'Dangerous Occurrence'),
    ], string='RIDDOR Category', compute='_compute_outcome')

    @api.depends('anyone_injured', 'worker_injured', 'fatal',
                 'specified_fracture', 'specified_amputation', 'specified_sight',
                 'specified_crush', 'specified_burn', 'specified_scalp',
                 'specified_unconscious', 'specified_enclosed_space',
                 'over_7_day', 'dangerous_occurrence', 'occupational_disease')
    def _compute_outcome(self):
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
