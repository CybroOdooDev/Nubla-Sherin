# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessPayment(models.Model):
    _name = 'fitness.payment'
    _description = 'Fitness Payment'

    subscription_id = fields.Many2one('fitness.subscription', string='Subscription', required=True)
    amount = fields.Float(string='Amount', required=True)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other')
    ], string='Payment Method', required=True, default='cash')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(FitnessPayment, self).create(vals_list)
        for record in records:
            # Logic to update subscription payment status could go here
            pass
        return records
