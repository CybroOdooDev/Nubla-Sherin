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


class NhsOncallProfile(models.Model):
    """A doctor's on-call commitment on a job plan: rota frequency/category
    (from the configurable supplement table) plus the predictable and
    unpredictable on-call work expressed as PAs."""
    _name = 'nhs.oncall.profile'
    _description = 'Job Plan On-Call Profile'
    _order = 'name'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. '1 in 8 (Category A)'."
    )
    supplement_rate_id = fields.Many2one(
        'nhs.oncall.supplement.rate',
        string='Supplement Rate',
        help="Frequency, category and availability supplement % from the"
             " configurable on-call supplement table."
    )
    frequency_n = fields.Integer(
        string='Frequency (1 in N)',
        related='supplement_rate_id.frequency_n',
        store=True,
        help="Rota frequency, from the supplement rate."
    )
    category = fields.Selection(
        related='supplement_rate_id.category',
        store=True,
        help="On-call category, from the supplement rate."
    )
    supplement_pct = fields.Float(
        string='Availability Supplement (%)',
        related='supplement_rate_id.supplement_pct',
        store=True,
        help="Availability supplement %, from the supplement rate."
    )
    predictable_pas = fields.Float(
        string='Predictable On-Call PAs',
        digits=(16, 2),
        help="Predictable on-call work expressed as PAs."
    )
    unpredictable_pas = fields.Float(
        string='Unpredictable On-Call PAs',
        digits=(16, 2),
        help="Unpredictable on-call work expressed as PAs."
    )
    total_oncall_pas = fields.Float(
        string='Total On-Call PAs',
        compute='_compute_total_oncall_pas',
        store=True,
        digits=(16, 2),
        help="predictable_pas + unpredictable_pas. Counted into the job plan's"
             " Additional Responsibility PA total."
    )
    job_plan_ids = fields.One2many(
        'nhs.job.plan',
        'oncall_profile_id',
        string='Job Plans',
        help="Job plans using this on-call profile."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Owning company."
    )

    @api.depends('predictable_pas', 'unpredictable_pas')
    def _compute_total_oncall_pas(self):
        """Sum predictable and unpredictable on-call PAs."""
        for profile in self:
            profile.total_oncall_pas = (profile.predictable_pas or 0.0) \
                + (profile.unpredictable_pas or 0.0)

    @api.depends('supplement_rate_id.name')
    def _compute_name(self):
        """Build the display name from the linked supplement rate."""
        for profile in self:
            profile.name = profile.supplement_rate_id.name or 'New On-Call Profile'
