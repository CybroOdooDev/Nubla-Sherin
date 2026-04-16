# -*- coding: utf-8 -*-
from odoo import models, fields, api

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

    # Special Offers
    special_offer_price = fields.Float(string='Special Offer Price')
    offer_start_date = fields.Date(string='Offer Start Date')
    offer_end_date = fields.Date(string='Offer End Date')
    current_price = fields.Float(string='Current Price', compute='_compute_current_price')

    @api.depends('price', 'special_offer_price', 'offer_start_date', 'offer_end_date')
    def _compute_current_price(self):
        today = fields.Date.context_today(self)
        for plan in self:
            if plan.special_offer_price > 0 and plan.offer_start_date and plan.offer_end_date:
                if plan.offer_start_date <= today <= plan.offer_end_date:
                    plan.current_price = plan.special_offer_price
                else:
                    plan.current_price = plan.price
            else:
                plan.current_price = plan.price
