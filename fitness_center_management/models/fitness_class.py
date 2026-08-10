# -*- coding: utf-8 -*-
from odoo import models, fields

class FitnessClass(models.Model):
    _name = 'fitness.class'
    _description = 'Fitness Class'

    name = fields.Char(string='Class Name', required=True)
    class_type = fields.Selection([
        ('yoga', 'Yoga'),
        ('zumba', 'Zumba'),
        ('crossfit', 'CrossFit'),
        ('cardio', 'Cardio'),
        ('strength', 'Strength Training'),
        ('other', 'Other')
    ], string='Class Type', required=True)
    max_capacity = fields.Integer(string='Max Capacity', default=20)
    branch_id = fields.Many2one('fitness.branch', string='Branch', tracking=True)
    default_duration = fields.Float(string='Default Duration (Hours)', default=1.0)
    difficulty = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], string='Difficulty', default='beginner')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
