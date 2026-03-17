# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
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
