from odoo import models, fields, api

class FitnessWorkoutLog(models.Model):
    _name = 'fitness.workout.log'
    _description = 'Workout Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    date = fields.Datetime(string='Workout Date', default=fields.Datetime.now, required=True, tracking=True)
    
    plan_id = fields.Many2one('fitness.workout.plan', string='Associated Plan')
    
    duration = fields.Float(string='Duration (Minutes)', required=True, tracking=True)
    calories_burned = fields.Float(string='Calories Burned', compute='_compute_calories_burned', store=True)
    
    notes = fields.Text(string='Workout Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='draft', tracking=True)
    
    # Detailed log lines
    line_ids = fields.One2many('fitness.workout.log.line', 'log_id', string='Exercises Performed')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fitness.workout.log') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.calories_burned', 'duration')
    def _compute_calories_burned(self):
        for record in self:
            if record.line_ids:
                record.calories_burned = sum(record.line_ids.mapped('calories_burned'))
            else:
                # Fallback estimation if no specific exercises are logged
                record.calories_burned = record.duration * 7.5


class FitnessWorkoutLogLine(models.Model):
    _name = 'fitness.workout.log.line'
    _description = 'Workout Log Line'

    log_id = fields.Many2one('fitness.workout.log', string='Workout Log', required=True, ondelete='cascade')
    exercise_id = fields.Many2one('fitness.exercise.library', string='Exercise', required=True)
    
    sets = fields.Integer(string='Sets', default=1)
    reps = fields.Integer(string='Reps', default=10)
    weight = fields.Float(string='Weight (kg/lbs)')
    duration_minutes = fields.Float(string='Duration (Mins)')
    
    calories_burned = fields.Float(string='Est. Calories', compute='_compute_calories', store=True)

    @api.depends('exercise_id', 'duration_minutes', 'sets', 'reps')
    def _compute_calories(self):
        for line in self:
            if line.exercise_id and line.duration_minutes > 0:
                line.calories_burned = line.exercise_id.calories_per_minute * line.duration_minutes
            elif line.exercise_id:
                # Estimate 0.5 minutes per set of 10 reps
                estimated_mins = line.sets * (line.reps / 10.0) * 0.5
                line.calories_burned = line.exercise_id.calories_per_minute * estimated_mins
            else:
                line.calories_burned = 0.0
