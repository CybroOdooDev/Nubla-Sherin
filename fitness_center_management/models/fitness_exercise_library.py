from odoo import models, fields, api

class FitnessExerciseLibrary(models.Model):
    _name = 'fitness.exercise.library'
    _description = 'Exercise Library'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Exercise Name', required=True, tracking=True)
    body_part = fields.Selection([
        ('chest', 'Chest'),
        ('back', 'Back'),
        ('legs', 'Legs'),
        ('arms', 'Arms'),
        ('shoulders', 'Shoulders'),
        ('core', 'Core'),
        ('full_body', 'Full Body'),
        ('cardio', 'Cardio')
    ], string='Target Body Part', required=True, tracking=True)
    
    equipment_required = fields.Selection([
        ('none', 'Bodyweight (None)'),
        ('dumbbell', 'Dumbbells'),
        ('barbell', 'Barbell'),
        ('machine', 'Machine'),
        ('kettlebell', 'Kettlebell'),
        ('band', 'Resistance Band')
    ], string='Equipment', default='none', tracking=True)
    
    difficulty = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], string='Difficulty Level', default='beginner')

    video_demo = fields.Char(string='Video Demo URL', help="Link to video demonstration")
    description = fields.Text(string='Instructions')
    
    # Metrics
    calories_per_minute = fields.Float(string='Calories Burned / Min', default=5.0)
