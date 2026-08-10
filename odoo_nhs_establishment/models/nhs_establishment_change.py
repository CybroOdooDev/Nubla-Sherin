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
from odoo.exceptions import UserError, ValidationError

CHANGE_TYPES = [
    ('create_post', 'Create Post'),
    ('delete_post', 'Delete Post'),
    ('increase_fte', 'Increase FTE'),
    ('decrease_fte', 'Decrease FTE'),
    ('reband', 'Re-band'),
    ('transfer', 'Transfer Between Teams'),
]

STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('workforce_approved', 'Workforce Approved'),
    ('finance_approved', 'Finance Approved'),
    ('applied', 'Applied'),
    ('rejected', 'Rejected'),
]


class NhsEstablishmentChange(models.Model):
    _name = 'nhs.establishment.change'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A controlled change to the establishment'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help="Change reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    change_type = fields.Selection(
        CHANGE_TYPES,
        string='Change Type',
        required=True,
        tracking=True,
        default='increase_fte',
        help="create_post / delete_post / increase_fte / decrease_fte / reband / transfer."
    )
    post_id = fields.Many2one(
        'nhs.establishment.post',
        string='Affected Post',
        tracking=True,
        help="Affected post (blank for create_post)."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Target Unit',
        tracking=True,
        help="Target unit for create_post / transfer."
    )

    # Proposed values (structured, per change_type)
    proposed_job_title = fields.Char(string='Proposed Job Title')
    proposed_staff_group_id = fields.Many2one('nhs.staff.group', string='Proposed Staff Group')
    proposed_band_id = fields.Many2one('nhs.afc.band', string='Proposed Band')
    proposed_is_medical = fields.Boolean(string='Proposed Medical / Non-AfC')
    proposed_manual_indicative_salary = fields.Monetary(
        string='Proposed Manual Salary', currency_field='currency_id')
    proposed_fte = fields.Float(string='Proposed FTE', digits=(16, 2))
    proposed_headcount = fields.Integer(string='Proposed Headcount', default=1)
    proposed_contracted_hours = fields.Float(
        string='Proposed Contracted Hours', digits=(16, 2), default=37.5)

    reason = fields.Text(
        string='Reason / Business Justification',
        required=True,
        help="Business justification for the change."
    )
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="When the change takes effect."
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id')
    cost_impact = fields.Monetary(
        string='Indicative Cost Impact',
        compute='_compute_cost_impact',
        currency_field='currency_id',
        help="Indicative annual pay-cost impact of the change, so approvers see the"
             " budget effect before signing off."
    )
    state = fields.Selection(
        STATES,
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )
    requested_by_id = fields.Many2one(
        'res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    workforce_approver_id = fields.Many2one(
        'res.users', string='Workforce Approver', readonly=True, tracking=True)
    workforce_approved_date = fields.Date(string='Workforce Approved On', readonly=True)
    finance_approver_id = fields.Many2one(
        'res.users', string='Finance Approver', readonly=True, tracking=True)
    finance_approved_date = fields.Date(string='Finance Approved On', readonly=True)
    applied_date = fields.Date(string='Applied On', readonly=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.depends(
        'change_type', 'proposed_fte', 'proposed_is_medical',
        'proposed_band_id.indicative_salary', 'proposed_manual_indicative_salary',
        'post_id.funded_fte', 'post_id.indicative_pay', 'post_id.is_medical',
        'post_id.band_id.indicative_salary', 'post_id.manual_indicative_salary',
        'company_id.nhs_on_cost_factor',
    )
    def _compute_cost_impact(self):
        for change in self:
            on_cost = change.company_id.nhs_on_cost_factor or 1.0
            post = change.post_id
            if change.change_type == 'create_post':
                salary = (change.proposed_manual_indicative_salary if change.proposed_is_medical
                          else (change.proposed_band_id.indicative_salary or 0.0))
                change.cost_impact = salary * (change.proposed_fte or 0.0) * on_cost
            elif change.change_type == 'delete_post':
                change.cost_impact = -(post.indicative_pay or 0.0)
            elif change.change_type in ('increase_fte', 'decrease_fte'):
                salary = post.manual_indicative_salary if post.is_medical else (
                    post.band_id.indicative_salary or 0.0)
                delta = (change.proposed_fte or 0.0) - post.funded_fte
                change.cost_impact = salary * delta * on_cost
            elif change.change_type == 'reband':
                old_salary = post.manual_indicative_salary if post.is_medical else (
                    post.band_id.indicative_salary or 0.0)
                new_salary = (change.proposed_manual_indicative_salary if change.proposed_is_medical
                              else (change.proposed_band_id.indicative_salary or 0.0))
                change.cost_impact = (new_salary - old_salary) * post.funded_fte * on_cost
            else:
                change.cost_impact = 0.0

    @api.constrains('change_type', 'post_id', 'org_unit_id')
    def _check_required_refs(self):
        for change in self:
            if change.change_type != 'create_post' and not change.post_id:
                raise ValidationError(
                    'An affected post must be selected for this change type.')
            if change.change_type in ('create_post', 'transfer') and not change.org_unit_id:
                raise ValidationError(
                    'A target unit must be selected for this change type.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'nhs.establishment.change') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for change in self:
            if change.state != 'draft':
                raise UserError('Only draft change requests can be submitted.')
        self.write({'state': 'submitted'})

    def _check_can_approve(self):
        if not self.env.user.has_group('odoo_nhs_establishment.group_nhs_workforce_manager'):
            raise UserError('Only a Workforce Manager can approve or apply establishment changes.')

    def action_workforce_approve(self):
        self._check_can_approve()
        for change in self:
            if change.state != 'submitted':
                raise UserError('Only submitted change requests can be workforce-approved.')
            vals = {
                'workforce_approver_id': self.env.user.id,
                'workforce_approved_date': fields.Date.context_today(self),
            }
            if change.company_id.nhs_change_control_single_stage:
                vals.update({
                    'state': 'finance_approved',
                    'finance_approver_id': self.env.user.id,
                    'finance_approved_date': fields.Date.context_today(self),
                })
            else:
                vals['state'] = 'workforce_approved'
            change.write(vals)

    def action_finance_approve(self):
        self._check_can_approve()
        for change in self:
            if change.state != 'workforce_approved':
                raise UserError('Only workforce-approved change requests can be finance-approved.')
            change.write({
                'state': 'finance_approved',
                'finance_approver_id': self.env.user.id,
                'finance_approved_date': fields.Date.context_today(self),
            })

    def action_apply(self):
        self._check_can_approve()
        for change in self:
            if change.state != 'finance_approved':
                raise UserError('Only finance-approved change requests can be applied.')
            change._apply_change()
            change.write({'state': 'applied', 'applied_date': fields.Date.context_today(self)})

    def action_reject(self):
        for change in self:
            if change.state in ('applied', 'rejected'):
                raise UserError(f"Cannot reject a change request in state '{change.state}'.")
            if not change.rejection_reason:
                raise UserError('Please provide a rejection reason before rejecting.')
        self.write({'state': 'rejected'})

    def _apply_change(self):
        self.ensure_one()
        Post = self.env['nhs.establishment.post'].with_context(nhs_change_control_apply=True)
        post = self.post_id.with_context(nhs_change_control_apply=True)
        if self.change_type == 'create_post':
            new_post = Post.create({
                'job_title': self.proposed_job_title,
                'org_unit_id': self.org_unit_id.id,
                'staff_group_id': self.proposed_staff_group_id.id,
                'band_id': self.proposed_band_id.id,
                'is_medical': self.proposed_is_medical,
                'manual_indicative_salary': self.proposed_manual_indicative_salary,
                'contracted_hours': self.proposed_contracted_hours,
                'funded_fte': self.proposed_fte,
                'funded_headcount': self.proposed_headcount,
                'status': 'active',
            })
            self.post_id = new_post
            new_post.message_post(body=f"Created by Establishment Change {self.name}: "
                                        f"{self.proposed_fte:.2f} FTE {self.proposed_job_title}.")
        elif self.change_type == 'delete_post':
            before = f"{post.funded_fte:.2f} FTE, status={post.status}"
            post.write({'status': 'deleted', 'active': False})
            post.message_post(
                body=f"Removed from establishment by Change {self.name}. Before: {before}.")
        elif self.change_type in ('increase_fte', 'decrease_fte'):
            before = post.funded_fte
            post.write({'funded_fte': self.proposed_fte})
            post.message_post(
                body=f"Funded FTE changed by Change {self.name}: "
                     f"{before:.2f} -> {self.proposed_fte:.2f}.")
        elif self.change_type == 'reband':
            before = post.band_id.name if post.band_id else 'Medical/Non-AfC'
            post.write({
                'band_id': self.proposed_band_id.id,
                'is_medical': self.proposed_is_medical,
                'manual_indicative_salary': self.proposed_manual_indicative_salary,
            })
            after = self.proposed_band_id.name if not self.proposed_is_medical else 'Medical/Non-AfC'
            post.message_post(
                body=f"Band changed by Change {self.name}: {before} -> {after}.")
        elif self.change_type == 'transfer':
            before = post.org_unit_id.complete_name
            post.write({'org_unit_id': self.org_unit_id.id})
            post.message_post(
                body=f"Transferred by Change {self.name}: "
                     f"{before} -> {self.org_unit_id.complete_name}.")
