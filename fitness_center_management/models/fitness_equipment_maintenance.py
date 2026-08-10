# -*- coding: utf-8 -*-
from odoo import models, fields

class FitnessEquipmentMaintenance(models.Model):
    _name = 'fitness.equipment.maintenance'
    _description = 'Fitness Equipment Maintenance'

    equipment_id = fields.Many2one('fitness.equipment', string='Equipment', required=True)
    maintenance_date = fields.Date(string='Maintenance Date', default=fields.Date.context_today)
    description = fields.Text(string='Description')
    cost = fields.Float(string='Maintenance Cost')
    technician = fields.Char(string='Technician/Vendor')
