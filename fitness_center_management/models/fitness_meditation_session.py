from odoo import models, fields

class FitnessMeditationSession(models.Model):
    _name = 'fitness.meditation.session'
    _description = 'Guided Meditation Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Session Title', required=True, tracking=True)
    focus = fields.Selection([
        ('sleep', 'Better Sleep'),
        ('stress', 'Stress Relief'),
        ('focus', 'Deep Focus'),
        ('morning', 'Morning Routine'),
        ('anxiety', 'Anxiety Control')
    ], string='Focus Area', required=True, tracking=True)
    
    duration = fields.Float(string='Duration (Minutes)', required=True)
    audio_url = fields.Char(string='Audio Track URL', help="Link to the guided audio file")
    
    description = fields.Text(string='Description')
    
    is_premium = fields.Boolean(string='Premium Only', default=False)
