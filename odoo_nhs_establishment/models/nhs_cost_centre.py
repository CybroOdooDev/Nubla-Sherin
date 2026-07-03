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


class NhsCostCentre(models.Model):
    _name = 'nhs.cost.centre'
    _description = 'NHS Cost Centre Reference Data'
    _order = 'code, name'

    name = fields.Char(
        string='Cost Centre Name',
        required=True,
        help="Descriptive name of the cost centre (e.g. 'Main Theatres')."
    )
    code = fields.Char(
        string='Cost Centre Code',
        required=True,
        help="The finance-system cost-centre code, entered on org units and posts."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help="Owning company."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'A cost centre with this code already exists for this company!'
    )
