# -*- coding: utf-8 -*-
from odoo import models, fields


class FitnessDietTemplate(models.Model):
    _name = 'fitness.diet.template'
    _description = 'Diet Plan Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Template Name', required=True, tracking=True)
    diet_category_id = fields.Many2one('fitness.diet.category', string='Diet Category')
    diet_type_id = fields.Many2one('fitness.diet.type', string='Diet Type')
    target_calories = fields.Integer(string='Target Calories / Day')
    description = fields.Text(string='Description')
    line_ids = fields.One2many('fitness.diet.template.line', 'template_id', string='Meals')
    active = fields.Boolean(default=True)


class FitnessDietTemplateLine(models.Model):
    _name = 'fitness.diet.template.line'
    _description = 'Diet Template Meal Line'

    template_id = fields.Many2one('fitness.diet.template', string='Template', required=True, ondelete='cascade')
    meal_type = fields.Selection([
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ], string='Meal Type', required=True)
    name = fields.Char(string='Description', required=True)
    calories = fields.Integer(string='Calories')
    protein = fields.Integer(string='Protein (g)')
    carbs = fields.Integer(string='Carbs (g)')
    fats = fields.Integer(string='Fats (g)')
    fiber = fields.Integer(string='Fiber (g)')
    sugar = fields.Integer(string='Sugar (g)')
    vitamins = fields.Char(string='Vitamins')
    minerals = fields.Char(string='Minerals')
