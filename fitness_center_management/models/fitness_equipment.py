# -*- coding: utf-8 -*-
from odoo import models, fields

class FitnessEquipment(models.Model):
    _name = 'fitness.equipment'
    _description = 'Fitness Equipment'

    name = fields.Char(string='Equipment Name', required=True)
    category = fields.Selection([
        ('cardio', 'Cardio'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
        ('other', 'Other')
    ], string='Category', required=True)
    serial_number = fields.Char(string='Serial Number')
    purchase_date = fields.Date(string='Purchase Date')
    warranty_expiry = fields.Date(string='Warranty Expiry')
    status = fields.Selection([
        ('operational', 'Operational'),
        ('maintenance', 'Under Maintenance'),
        ('broken', 'Broken'),
        ('disposed', 'Disposed')
    ], string='Status', default='operational')
    location = fields.Char(string='Location')
    cost = fields.Float(string='Cost')
