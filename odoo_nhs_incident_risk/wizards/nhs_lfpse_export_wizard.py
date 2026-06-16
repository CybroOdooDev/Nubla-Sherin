from odoo import api, fields, models


class NhsLfpseExportWizard(models.TransientModel):
    _name = 'nhs.lfpse.export.wizard'
    _description = 'LFPSE Export Wizard'

    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True, default=fields.Date.today)
    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ], string='Format', required=True, default='csv')
    incident_ids = fields.Many2many('nhs.incident', string='Incidents to Export',
                                    compute='_compute_incidents')
    incident_count = fields.Integer(compute='_compute_incidents')

    @api.depends('date_from', 'date_to')
    def _compute_incidents(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                incidents = self.env['nhs.incident'].search([
                    ('lfpse_state', '=', 'pending'),
                    ('occurred_at', '>=', fields.Datetime.from_string(
                        str(rec.date_from) + ' 00:00:00')),
                    ('occurred_at', '<=', fields.Datetime.from_string(
                        str(rec.date_to) + ' 23:59:59')),
                ])
                rec.incident_ids = incidents
                rec.incident_count = len(incidents)
            else:
                rec.incident_ids = False
                rec.incident_count = 0

    def action_export(self):
        self.ensure_one()
        if not self.incident_ids:
            from odoo.exceptions import UserError
            raise UserError('No pending incidents found in the selected date range.')
        batch = self.env['nhs.lfpse.submission'].create({
            'export_format': self.export_format,
            'incident_ids': [(6, 0, self.incident_ids.ids)],
        })
        return batch.action_export()
