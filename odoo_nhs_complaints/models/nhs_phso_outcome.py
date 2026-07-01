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


class NhsPhsoOutcome(models.Model):
    _name = 'nhs.phso.outcome'
    _description = 'PHSO Case Outcome'
    _order = 'sequence, name'

    name = fields.Char(string='Outcome', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Selection([
        ('success', 'Green — Not Upheld'),
        ('warning', 'Orange — Partly Upheld'),
        ('danger', 'Red — Upheld'),
        ('info', 'Blue'),
        ('secondary', 'Grey'),
    ], string='Badge Colour', default='secondary',
       help='Colour used for this outcome on kanban cards and list badges.')
    active = fields.Boolean(default=True,
                            help='Uncheck to hide this outcome without deleting it.')
