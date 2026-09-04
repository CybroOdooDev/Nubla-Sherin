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


class NhsServiceObjective(models.Model):
    """A directorate/service-level objective (e.g. 'Reduce A&E wait times')
    that individual doctors' personal job-plan objectives can link back to -
    the build spec's 'personal objectives on the plan (linked to service
    objectives)' (5.4). Kept as a proper reference model, matching the rest
    of the module's reference data (session categories, on-call supplement
    table), rather than a free-text field: reusable across doctors, and
    groupable/reportable in a way free text on nhs.job.plan.objective never
    could be."""
    _name = 'nhs.service.objective'
    _description = 'Service Objective'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        help="e.g. 'Reduce A&E wait times', 'Improve theatre utilisation'."
    )
    description = fields.Text(
        string='Description',
        help="Detail on what the service objective covers."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Directorate / Unit',
        help="Leave blank for a trust-wide objective; set to scope this"
             " objective to one directorate/unit."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help="Leave blank to make this objective available to every company."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )
