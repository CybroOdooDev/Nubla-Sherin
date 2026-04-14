# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessDietPlan(models.Model):
    _name = 'fitness.diet.plan'
    _description = 'Fitness Diet Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Name', required=True, tracking=True)
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    trainer_id = fields.Many2one('fitness.trainer', string='Nutritionist/Trainer')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date')
    total_calories = fields.Integer(string='Target Calories / Day')
    meal_ids = fields.One2many('fitness.diet.meal', 'plan_id', string='Meals')

class FitnessDietMeal(models.Model):
    _name = 'fitness.diet.meal'
    _description = 'Fitness Diet Meal'

    plan_id = fields.Many2one('fitness.diet.plan', string='Diet Plan', ondelete='cascade')
    meal_type = fields.Selection([
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack')
    ], string='Meal Type', required=True)
    name = fields.Char(string='Description (e.g. Chicken Salad)', required=True)
    calories = fields.Integer(string='Calories')
    protein = fields.Integer(string='Protein (g)')
    carbs = fields.Integer(string='Carbs (g)')
    fats = fields.Integer(string='Fats (g)')
