# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FitnessDietPlan(models.Model):
    _name = 'fitness.diet.plan'
    _description = 'Fitness Diet Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Name', required=True, tracking=True)
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    trainer_id = fields.Many2one('fitness.trainer', string='Dietitian/Trainer')
    diet_category_id = fields.Many2one('fitness.diet.category', string='Diet Category')
    diet_type_id = fields.Many2one('fitness.diet.type', string='Diet Type')
    template_id = fields.Many2one('fitness.diet.template', string='Diet Template')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date')
    total_calories = fields.Integer(string='Target Calories / Day')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    charges = fields.Float(string='Charges')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    meal_ids = fields.One2many('fitness.diet.meal', 'plan_id', string='Meals')

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_load_from_template(self):
        """Load meals from the selected diet template."""
        self.ensure_one()
        if not self.template_id:
            return
        for line in self.template_id.line_ids:
            self.env['fitness.diet.meal'].create({
                'plan_id': self.id,
                'meal_type': line.meal_type,
                'name': line.name,
                'calories': line.calories,
                'protein': line.protein,
                'carbs': line.carbs,
                'fats': line.fats,
                'fiber': line.fiber,
                'sugar': line.sugar,
                'vitamins': line.vitamins,
                'minerals': line.minerals,
            })
        if self.template_id.target_calories:
            self.total_calories = self.template_id.target_calories

    def action_create_invoice(self):
        """Create an invoice for the diet plan charges."""
        self.ensure_one()
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        partner = self.member_id.partner_id
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.member_id.name,
                'email': self.member_id.email,
                'phone': self.member_id.phone,
            })
            self.member_id.partner_id = partner
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Diet Plan: %s' % self.name,
                'quantity': 1,
                'price_unit': self.charges,
            })],
        })
        self.invoice_id = invoice
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


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
    fiber = fields.Integer(string='Fiber (g)')
    sugar = fields.Integer(string='Sugar (g)')
    vitamins = fields.Char(string='Vitamins')
    minerals = fields.Char(string='Minerals')
