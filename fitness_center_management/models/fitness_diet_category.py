# -*- coding: utf-8 -*-
from odoo import models, fields


class FitnessDietCategory(models.Model):
    _name = 'fitness.diet.category'
    _description = 'Diet Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
