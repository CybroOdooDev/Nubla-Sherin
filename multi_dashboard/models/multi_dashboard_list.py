# -*- coding: utf-8 -*-
from odoo import fields, models


class MultiDashboardList(models.Model):
    """Model to link charts with fields for multi dashboard."""
    _name = 'multi.dashboard.list'
    _description = 'Multi Dashboard List'
    _order = 'id desc'

    chart_id = fields.Many2one('multi.dashboard.charts',
                               'Chart',
                               help='The chart this list belongs to',
                               ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields',
                               'Field',
                               domain="[('model_id', '=', parent.model_id), ('ttype', 'not in', ('binary', 'reference', 'serialized'))]")
    sequence = fields.Integer('Sequence', default=10,
                              help='Sequence for ordering fields in the list')
