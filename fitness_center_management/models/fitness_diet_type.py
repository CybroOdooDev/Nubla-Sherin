# -*- coding: utf-8 -*-
from odoo import models, fields


class FitnessDietType(models.Model):
    _name = 'fitness.diet.type'
    _description = 'Diet Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
