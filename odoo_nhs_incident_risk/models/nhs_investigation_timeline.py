from odoo import fields, models


class NhsInvestigationTimeline(models.Model):
    _name = 'nhs.investigation.timeline'
    _description = 'Investigation Chronology Entry'
    _order = 'happened_at'

    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       required=True, ondelete='cascade')
    happened_at = fields.Datetime(string='Date / Time', required=True)
    entry = fields.Text(string='Entry', required=True)
    source = fields.Char(string='Evidence Source',
                         help='e.g. Staff statement, CCTV, care notes')
