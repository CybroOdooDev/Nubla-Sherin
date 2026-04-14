from odoo import models, fields

class FitnessChallenge(models.Model):
    _name = 'fitness.challenge'
    _description = 'Community Fitness Challenge'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Challenge Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    
    target_metric = fields.Selection([
        ('workouts', 'Total Workouts Logged'),
        ('calories', 'Total Calories Burned'),
        ('distance', 'Distance (km)'),
        ('streak', 'Consecutive Days Active')
    ], string='Goal Metric', required=True)
    
    target_value = fields.Float(string='Target Amount', required=True)
    
    participant_ids = fields.Many2many('fitness.member', string='Participants')
    
    state = fields.Selection([
        ('draft', 'Upcoming'),
        ('active', 'Active'),
        ('closed', 'Completed')
    ], string='Status', default='draft', tracking=True)
    
    cover_image = fields.Image(string='Cover Photo')
