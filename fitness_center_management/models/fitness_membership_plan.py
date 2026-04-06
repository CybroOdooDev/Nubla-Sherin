# -*- coding: utf-8 -*-
from odoo import models, fields

class FitnessMembershipPlan(models.Model):
    _name = 'fitness.membership.plan'
    _description = 'Fitness Membership Plan'

    name = fields.Char(string='Name', required=True)
    plan_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom')
    ], string='Plan Type', required=True, default='monthly')
    duration_months = fields.Integer(string='Duration (Months)', required=True, default=1)
    price = fields.Float(string='Price', required=True)
    features = fields.Text(string='Features')
    max_freeze_days = fields.Integer(string='Max Freeze Days', default=0)
    active = fields.Boolean(string='Active', default=True)
