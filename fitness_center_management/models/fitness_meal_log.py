from odoo import models, fields, api

class FitnessMealLog(models.Model):
    _name = 'fitness.meal.log'
    _description = 'Member Daily Meal Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    date = fields.Date(string='Log Date', default=fields.Date.context_today, required=True, tracking=True)
    
    meal_type = fields.Selection([
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack / Supplements')
    ], string='Meal Type', required=True)
    
    food_id = fields.Many2one('fitness.food.item', string='Food Item', required=True)
    servings = fields.Float(string='Number of Servings', default=1.0)
    
    # Computed Nutrition
    total_calories = fields.Float(string='Total Calories', compute='_compute_nutrition', store=True)
    total_protein = fields.Float(string='Total Protein (g)', compute='_compute_nutrition', store=True)
    total_carbs = fields.Float(string='Total Carbs (g)', compute='_compute_nutrition', store=True)
    total_fats = fields.Float(string='Total Fats (g)', compute='_compute_nutrition', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fitness.meal.log') or 'New'
        return super().create(vals_list)

    @api.depends('food_id', 'servings')
    def _compute_nutrition(self):
        for log in self:
            if log.food_id and log.servings:
                log.total_calories = log.food_id.calories * log.servings
                log.total_protein = log.food_id.protein * log.servings
                log.total_carbs = log.food_id.carbs * log.servings
                log.total_fats = log.food_id.fats * log.servings
            else:
                log.total_calories = 0.0
                log.total_protein = 0.0
                log.total_carbs = 0.0
                log.total_fats = 0.0
