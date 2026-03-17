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
