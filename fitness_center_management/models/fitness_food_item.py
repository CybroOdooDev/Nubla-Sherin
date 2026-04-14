from odoo import models, fields

class FitnessFoodItem(models.Model):
    _name = 'fitness.food.item'
    _description = 'Food Item Database'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Food Name', required=True, tracking=True)
    barcode = fields.Char(string='Barcode', help='For easy scanning support later')
    
    serving_size = fields.Char(string='Serving Size', default='100g')
    
    calories = fields.Float(string='Calories', required=True, tracking=True)
    protein = fields.Float(string='Protein (g)', required=True)
    carbs = fields.Float(string='Carbohydrates (g)', required=True)
    fats = fields.Float(string='Fats (g)', required=True)
    
    is_verified = fields.Boolean(string='Verified by System', default=False)
