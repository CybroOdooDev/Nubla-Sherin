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


class NhsRiskReview(models.Model):
    _name = 'nhs.risk.review'
    _description = 'Risk Review Log Entry'
    _order = 'reviewed_at desc'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade',
                              help='The risk register entry this review log belongs to.')
    reviewed_at = fields.Datetime(string='Reviewed At', required=True,
                                  default=fields.Datetime.now,
                                  help='The date and time this review was conducted.')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', required=True,
                                  default=lambda self: self.env.user,
                                  help='The person who conducted this review.')
    prev_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='Previous Consequence',
        help='The consequence score (1–5) before this review was conducted.')
    prev_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='Previous Likelihood',
        help='The likelihood score (1–5) before this review was conducted.')
    new_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='New Consequence',
        help='The updated consequence score (1–5) following this review.')
    new_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='New Likelihood',
        help='The updated likelihood score (1–5) following this review.')
    commentary = fields.Text(string='Commentary',
                             help='Narrative from the reviewer explaining the outcome of the review, '
                                  'any changes made to the risk score, and the rationale for the decision.')
    decision = fields.Selection([
        ('no_change', 'No Change'),
        ('rescore', 'Re-scored'),
        ('escalate', 'Escalated'),
        ('deescalate', 'De-escalated'),
        ('close', 'Risk Closed'),
    ], string='Decision', required=True, default='no_change',
       help='The outcome of this review: whether the risk score changed, '
            'whether the risk was escalated or de-escalated to another register, or closed.')
