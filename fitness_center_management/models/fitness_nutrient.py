# -*- coding: utf-8 -*-
from odoo import models, fields


class FitnessNutrient(models.Model):
    _name = 'fitness.nutrient'
    _description = 'Nutrient'
    _order = 'name'

    name = fields.Char(string='Nutrient Name', required=True)
    nutrient_type = fields.Selection([
        ('vitamin', 'Vitamin'),
        ('mineral', 'Mineral'),
        ('amino_acid', 'Amino Acid'),
        ('fatty_acid', 'Fatty Acid'),
        ('other', 'Other'),
    ], string='Type', default='vitamin')
    unit = fields.Char(string='Unit', default='mg', help='e.g. mg, mcg, IU')
    description = fields.Text(string='Description')
    daily_value = fields.Float(string='Daily Recommended Value')


class FitnessFoodNutrient(models.Model):
    _name = 'fitness.food.nutrient'
    _description = 'Food Nutrient Line'

    food_id = fields.Many2one('fitness.food.item', string='Food Item', required=True, ondelete='cascade')
    nutrient_id = fields.Many2one('fitness.nutrient', string='Nutrient', required=True)
    amount = fields.Float(string='Amount')
    unit = fields.Char(string='Unit', related='nutrient_id.unit', readonly=True)
