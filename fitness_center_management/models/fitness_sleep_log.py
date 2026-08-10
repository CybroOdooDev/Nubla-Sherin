from odoo import models, fields, api

class FitnessSleepLog(models.Model):
    _name = 'fitness.sleep.log'
    _description = 'Member Sleep Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Ref', compute='_compute_name', store=True)
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    date = fields.Date(string='Log Date', default=fields.Date.context_today, required=True, tracking=True)
    
    duration = fields.Float(string='Total Sleep (Hours)', required=True, tracking=True)
    deep_sleep = fields.Float(string='Deep Sleep (Hours)', help="Estimated deep sleep duration")
    rem_sleep = fields.Float(string='REM Sleep (Hours)')
    
    sleep_score = fields.Integer(string='Sleep Score (0-100)', tracking=True)
    stress_score = fields.Integer(string='Stress Score (0-100)', help="Daily stress level computation")

    notes = fields.Text(string='Notes / Dreams')
    
    # Wearable Sync
    source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('apple', 'Apple Health'),
        ('fitbit', 'Fitbit'),
        ('garmin', 'Garmin')
    ], string='Data Source', default='manual')

    @api.depends('member_id', 'date')
    def _compute_name(self):
        for log in self:
            date_str = str(log.date) if log.date else ''
            member_name = log.member_id.name if log.member_id else ''
            log.name = f"Sleep: {member_name} - {date_str}"
