# -*- coding: utf-8 -*-
from odoo import fields, models


class MultiDashboardTodo(models.Model):
    """Model to manage to-do items for multi dashboard charts."""
    _name = 'multi.dashboard.todo'
    _description = 'Multi Dashboard Todo Items'
    _order = 'sequence, id'

    name = fields.Char('Description',
                       required=True,
                       help='Description of the to-do item')
    sequence = fields.Integer('Sequence', default=10,
                              help='Sequence for ordering to-do items')
    is_done = fields.Boolean('Done', default=False,
                             help='Mark the to-do item as done')
    chart_id = fields.Many2one('multi.dashboard.charts',
                               'Chart',
                               ondelete='cascade',
                               help='The chart this to-do item belongs to')
