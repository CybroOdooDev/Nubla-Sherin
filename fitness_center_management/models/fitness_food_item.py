from odoo import models, fields

class FitnessFoodItem(models.Model):
    _name = 'fitness.food.item'
    _description = 'Food Item Database'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Food Name', required=True, tracking=True)
    barcode = fields.Char(string='Barcode', help='For easy scanning support later')
    
    food_group = fields.Selection([
        ('protein', 'Protein'),
        ('carbs', 'Carbohydrates'),
        ('fats', 'Fats'),
        ('dairy', 'Dairy'),
        ('fruits', 'Fruits'),
        ('vegetables', 'Vegetables'),
        ('grains', 'Grains'),
        ('other', 'Other'),
    ], string='Food Group')
    serving_size = fields.Char(string='Serving Size', default='100g')
    
    calorie_unit = fields.Selection([
        ('kcal', 'kcal'),
        ('kj', 'kJ'),
    ], string='Calorie Unit', default='kcal')
    calories = fields.Float(string='Calories', required=True, tracking=True)
    protein = fields.Float(string='Protein (g)', required=True)
    carbs = fields.Float(string='Carbohydrates (g)', required=True)
    fats = fields.Float(string='Fats (g)', required=True)
    
    nutrient_ids = fields.One2many('fitness.food.nutrient', 'food_id', string='Nutrients')
    is_verified = fields.Boolean(string='Verified by System', default=False)
