# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessTrainer(models.Model):
    _name = 'fitness.trainer'
    _description = 'Fitness Trainer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee Link', ondelete='cascade')
    specialization_ids = fields.Many2many('hr.skill', string='Specializations')
    certification = fields.Text(string='Certifications')
    experience_years = fields.Integer(string='Years of Experience')
    hourly_rate = fields.Float(string='Hourly Rate')
    bio = fields.Html(string='Biography')
    photo = fields.Binary(string='Photo', related='employee_id.image_1920', readonly=False)
    rating = fields.Selection([
        ('0', 'Low'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Rating', compute='_compute_rating', store=True, default='0')
 
    @api.depends('name')
    def _compute_rating(self):
        for record in self:
            # Placeholder for rating logic
            record.rating = '5'
