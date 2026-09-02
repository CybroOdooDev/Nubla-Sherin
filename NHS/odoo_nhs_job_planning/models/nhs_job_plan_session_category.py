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

CLASSIFICATIONS = [
    ('dcc', 'Direct Clinical Care'),
    ('spa', 'Supporting Professional Activities'),
    ('additional', 'Additional Responsibility'),
    ('external', 'External Duty'),
]


class NhsJobPlanSessionCategory(models.Model):
    """A reusable session/activity category (e.g. 'Outpatient Clinic') that a
    timetable line can pick to pre-fill its classification and description."""
    _name = 'nhs.job.plan.session.category'
    _description = 'Job Plan Session Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        help="e.g. 'Outpatient Clinic', 'Theatre List', 'CPD/Study'."
    )
    code = fields.Char(
        string='Code',
        help="Short internal code."
    )
    default_classification = fields.Selection(
        CLASSIFICATIONS,
        string='Default Classification',
        help="Pre-fills a timetable line's DCC/SPA/Additional/External"
             " classification when this category is picked."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help="Leave blank to make this category available to every company."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )
