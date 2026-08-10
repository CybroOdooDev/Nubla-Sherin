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


class NhsRecruitmentChannel(models.Model):
    """Reference data for where a vacancy was advertised (NHS Jobs, Trac,
    internal, external site, ...)."""
    _name = 'nhs.recruitment.channel'
    _description = 'Advertising channel'
    _order = 'sequence, name'

    name = fields.Char(string='Channel', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_external = fields.Boolean(string='External', default=True)
    active = fields.Boolean(string='Active', default=True)

    _name_uniq = models.Constraint(
        'unique(name)',
        'This advertising channel already exists.'
    )
