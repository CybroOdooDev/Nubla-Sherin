# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FitnessReport(models.Model):
    _name = 'fitness.report'
    _description = 'Fitness Report (BMI / BMR / BFP)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)

    # Measurements
    height = fields.Float(string='Height (cm)')
    weight = fields.Float(string='Weight (kg)')
    age = fields.Integer(string='Age', related='member_id.age', readonly=True)
    gender = fields.Selection(related='member_id.gender', readonly=True)
    waist = fields.Float(string='Waist (cm)')
    hip = fields.Float(string='Hip (cm)')
    neck = fields.Float(string='Neck (cm)')

    # Computed Metrics
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    bmi_category = fields.Selection([
        ('underweight', 'Underweight'),
        ('normal', 'Normal'),
        ('overweight', 'Overweight'),
        ('obese', 'Obese'),
    ], string='BMI Category', compute='_compute_bmi', store=True)
    bmr = fields.Float(string='BMR (kcal/day)', compute='_compute_bmr', store=True,
                        help='Basal Metabolic Rate using Mifflin-St Jeor equation')
    bfp = fields.Float(string='Body Fat %', compute='_compute_bfp', store=True,
                        help='Body Fat Percentage using Deurenberg formula')

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fitness.report') or 'New'
        return super().create(vals_list)

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.height and rec.weight:
                h = rec.height / 100.0
                rec.bmi = round(rec.weight / (h ** 2), 2)
                if rec.bmi < 18.5:
                    rec.bmi_category = 'underweight'
                elif rec.bmi < 25:
                    rec.bmi_category = 'normal'
                elif rec.bmi < 30:
                    rec.bmi_category = 'overweight'
                else:
                    rec.bmi_category = 'obese'
            else:
                rec.bmi = 0.0
                rec.bmi_category = False

    @api.depends('weight', 'height', 'age', 'gender')
    def _compute_bmr(self):
        for rec in self:
            if rec.weight and rec.height and rec.age:
                if rec.gender == 'male':
                    rec.bmr = round((10 * rec.weight) + (6.25 * rec.height) - (5 * rec.age) + 5, 2)
                else:
                    rec.bmr = round((10 * rec.weight) + (6.25 * rec.height) - (5 * rec.age) - 161, 2)
            else:
                rec.bmr = 0.0

    @api.depends('bmi', 'age', 'gender')
    def _compute_bfp(self):
        for rec in self:
            if rec.bmi and rec.age:
                gender_val = 1 if rec.gender == 'male' else 0
                rec.bfp = round((1.20 * rec.bmi) + (0.23 * rec.age) - (10.8 * gender_val) - 5.4, 2)
            else:
                rec.bfp = 0.0
