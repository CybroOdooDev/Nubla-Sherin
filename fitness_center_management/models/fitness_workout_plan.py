# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessWorkoutPlan(models.Model):
    _name = 'fitness.workout.plan'
    _description = 'Fitness Workout Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Name', required=True, tracking=True)
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    trainer_id = fields.Many2one('fitness.trainer', string='Trainer')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date')
    exercise_ids = fields.One2many('fitness.workout.exercise', 'plan_id', string='Exercises')

class FitnessWorkoutExercise(models.Model):
    _name = 'fitness.workout.exercise'
    _description = 'Fitness Workout Exercise'

    plan_id = fields.Many2one('fitness.workout.plan', string='Workout Plan', ondelete='cascade')
    exercise_id = fields.Many2one('fitness.exercise.library', string='Exercise')
    name = fields.Char(string='Exercise Name', required=True)
    description = fields.Text(string='Description/Instructions')
    sets = fields.Integer(string='Sets', default=3)
    reps = fields.Integer(string='Reps', default=10)
    duration_minutes = fields.Integer(string='Duration (mins)')

    @api.onchange('exercise_id')
    def _onchange_exercise_id(self):
        if self.exercise_id:
            self.name = self.exercise_id.name
            self.description = self.exercise_id.description
