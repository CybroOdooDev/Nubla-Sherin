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


class NhsCostCentre(models.Model):
    """Finance cost-centre reference data, rolling up the funded FTE, in-post
    FTE and indicative pay spend of the posts charged against it."""
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
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        help="Currency used for the budget and pay-cost figures."
    )
    budget_amount = fields.Monetary(
        string='Annual Budget',
        currency_field='currency_id',
        help="Annual pay-budget allocation for this cost centre, as agreed with Finance."
    )
    post_ids = fields.One2many(
        'nhs.establishment.post',
        'cost_centre',
        string='Posts',
        help="Establishment posts charged to this cost centre."
    )
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_rollups',
        store=True,
    )
    funded_fte = fields.Float(
        string='Funded FTE',
        compute='_compute_rollups',
        store=True,
        digits=(16, 2),
        help="Total funded FTE of active/frozen posts charged to this cost centre."
    )
    in_post_fte = fields.Float(
        string='In-Post FTE',
        compute='_compute_rollups',
        store=True,
        digits=(16, 2),
    )
    vacant_fte = fields.Float(
        string='Vacant FTE',
        compute='_compute_rollups',
        store=True,
        digits=(16, 2),
    )
    indicative_pay_total = fields.Monetary(
        string='Indicative Annual Spend',
        compute='_compute_rollups',
        store=True,
        currency_field='currency_id',
        help="Sum of indicative annual pay for active/frozen posts charged to this cost centre."
    )
    budget_variance = fields.Monetary(
        string='Budget Variance',
        compute='_compute_rollups',
        store=True,
        currency_field='currency_id',
        help="Annual Budget minus Indicative Annual Spend. Negative means the cost"
             " centre's funded establishment is projected to overspend its budget."
    )
    budget_utilization = fields.Float(
        string='Budget Utilisation',
        compute='_compute_rollups',
        store=True,
        digits=(16, 3),
        help="Indicative Annual Spend / Annual Budget, e.g. 0.85 for 85%."
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

    @api.depends('post_ids.status', 'post_ids.funded_fte', 'post_ids.in_post_fte',
                 'post_ids.vacant_fte', 'post_ids.indicative_pay', 'budget_amount')
    def _compute_rollups(self):
        """Roll up post counts, FTE and pay figures onto the cost centre."""
        for centre in self:
            posts = centre.post_ids.filtered(lambda p: p.status in ('active', 'frozen'))
            centre.post_count = len(posts)
            centre.funded_fte = sum(posts.mapped('funded_fte'))
            centre.in_post_fte = sum(posts.mapped('in_post_fte'))
            centre.vacant_fte = sum(posts.mapped('vacant_fte'))
            centre.indicative_pay_total = sum(posts.mapped('indicative_pay'))
            centre.budget_variance = centre.budget_amount - centre.indicative_pay_total
            centre.budget_utilization = (
                centre.indicative_pay_total / centre.budget_amount
                if centre.budget_amount else 0.0
            )

    def action_view_posts(self):
        """Open the posts charged to this cost centre."""
        self.ensure_one()
        return {
            'name': f'Posts — {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.post',
            'view_mode': 'list,form',
            'domain': [('cost_centre', '=', self.id), ('status', 'in', ('active', 'frozen'))],
            'context': {'default_cost_centre': self.id},
        }
