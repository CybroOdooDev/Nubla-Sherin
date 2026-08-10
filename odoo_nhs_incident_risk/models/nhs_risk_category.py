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


class NhsRiskCategory(models.Model):
    _name = 'nhs.risk.category'
    _description = 'Risk Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True,
                       help='The name of this risk category (e.g. Clinical, Financial, Operational, Reputational).')
    description = fields.Text(string='Description',
                               help='Optional description of the types of risk that fall within this category.')
    appetite_threshold = fields.Integer(
        string='Appetite Threshold (1–25)', default=6,
        help='Risks with current_rating above this threshold are flagged outside appetite.')
    active = fields.Boolean(default=True,
                            help='Untick to archive this category. Archived categories are hidden from new risk entries.')
