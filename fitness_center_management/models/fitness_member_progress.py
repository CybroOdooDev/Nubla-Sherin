# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessMemberProgress(models.Model):
    _name = 'fitness.member.progress'
    _description = 'Fitness Member Progress Tracking'
    _order = 'date desc'

    member_id = fields.Many2one('fitness.member', string='Member', required=True)
    date = fields.Date(string='Date Recorded', required=True, default=fields.Date.context_today)
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)', related='member_id.height', readonly=True)
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    body_fat_percent = fields.Float(string='Body Fat %')
    muscle_mass = fields.Float(string='Muscle Mass (kg)')
    notes = fields.Text(string='Notes')
    
    before_photo = fields.Image(string='Before Photo', max_width=512, max_height=512)
    after_photo = fields.Image(string='After Photo', max_width=512, max_height=512)

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for record in self:
            if record.height and record.weight:
                height_m = record.height / 100.0
                record.bmi = round(record.weight / (height_m ** 2), 2)
            else:
                record.bmi = 0.0
