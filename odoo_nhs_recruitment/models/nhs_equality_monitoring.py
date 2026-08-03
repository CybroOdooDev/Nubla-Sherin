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
from odoo import api, fields, models


class NhsEqualityMonitoring(models.Model):
    """Equality & diversity monitoring data, deliberately held on a SEPARATE
    model with its own access control so it can never influence (or appear
    to influence) selection — collected but not shown on the application
    form or to the selection panel; reported only in aggregate."""
    _name = 'nhs.equality.monitoring'
    _description = 'Equality monitoring (segregated)'

    application_id = fields.Many2one(
        'nhs.application', string='Application', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        related='application_id.company_id', string='Company', store=True, readonly=True)
    age_band = fields.Selection([
        ('16_24', '16-24'), ('25_34', '25-34'), ('35_44', '35-44'),
        ('45_54', '45-54'), ('55_64', '55-64'), ('65_plus', '65+'),
        ('prefer_not', 'Prefer Not to Say'),
    ], string='Age Band')
    ethnicity = fields.Selection([
        ('white', 'White'), ('mixed', 'Mixed / Multiple Ethnic Groups'),
        ('asian', 'Asian / Asian British'), ('black', 'Black / African / Caribbean / Black British'),
        ('other', 'Other Ethnic Group'), ('prefer_not', 'Prefer Not to Say'),
    ], string='Ethnicity')
    disability = fields.Selection([
        ('yes', 'Yes'), ('no', 'No'), ('prefer_not', 'Prefer Not to Say'),
    ], string='Disability')
    sex = fields.Selection([
        ('female', 'Female'), ('male', 'Male'), ('prefer_not', 'Prefer Not to Say'),
    ], string='Sex')
    religion = fields.Char(string='Religion / Belief')
    sexual_orientation = fields.Char(string='Sexual Orientation')

    @api.model
    def get_aggregate_stats(self, domain=None):
        """Aggregate, de-identified counts by field — never returns per-record data."""
        records = self.search(domain or [])
        result = {}
        for field_name in ('age_band', 'ethnicity', 'disability', 'sex'):
            counts = {}
            for record in records:
                key = dict(record._fields[field_name].selection).get(
                    record[field_name]) or 'Not Provided'
                counts[key] = counts.get(key, 0) + 1
            result[field_name] = counts
        return result
