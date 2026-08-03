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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class NhsOffer(models.Model):
    """An offer to a successful candidate, carrying the embedded
    pre-employment check set — the gate between a conditional offer and an
    unconditional start."""
    _name = 'nhs.offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Offer'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default='New')
    application_id = fields.Many2one(
        'nhs.application', string='Application', required=True, ondelete='cascade', tracking=True)
    candidate_id = fields.Many2one(
        related='application_id.candidate_id', string='Candidate', store=True, readonly=True)
    vacancy_id = fields.Many2one(
        related='application_id.vacancy_id', string='Vacancy', store=True, readonly=True)
    company_id = fields.Many2one(
        related='vacancy_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    band_id = fields.Many2one(
        related='vacancy_id.band_id', string='Band', store=True, readonly=True)
    pay_point = fields.Char(string='Pay Point')
    salary = fields.Monetary(string='Offered Salary', currency_field='currency_id')
    start_date = fields.Date(string='Proposed Start Date', tracking=True)
    fte = fields.Float(string='FTE', related='vacancy_id.fte', store=True, readonly=False)
    hours = fields.Float(string='Hours per Week')
    offer_type = fields.Selection([
        ('conditional', 'Conditional'),
        ('unconditional', 'Unconditional'),
    ], string='Offer Type', default='conditional', required=True, tracking=True)
    state = fields.Selection([
        ('made', 'Made'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='made', required=True, tracking=True)
    check_ids = fields.One2many('nhs.check', 'offer_id', string='Pre-Employment Checks')
    check_count = fields.Integer(string='Check Count', compute='_compute_check_status', store=True)
    checks_cleared_count = fields.Integer(string='Cleared', compute='_compute_check_status', store=True)
    all_checks_cleared = fields.Boolean(
        string='All Checks Cleared', compute='_compute_check_status', store=True,
        help="True when every required check is cleared — enables an unconditional offer/start."
    )
    has_concern = fields.Boolean(
        string='Check Concern', compute='_compute_check_status', store=True,
        help="At least one check has been flagged 'concern' — progression is paused for review."
    )
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('nhs.offer') or 'New'
        offers = super().create(vals_list)
        offers._generate_checks()
        return offers

    @api.depends('check_ids.status')
    def _compute_check_status(self):
        for offer in self:
            checks = offer.check_ids
            required = checks.filtered(lambda c: c.status != 'not_required')
            offer.check_count = len(checks)
            offer.checks_cleared_count = len(required.filtered(lambda c: c.status == 'cleared'))
            offer.all_checks_cleared = bool(required) and all(
                c.status == 'cleared' for c in required)
            offer.has_concern = bool(checks.filtered(lambda c: c.status == 'concern'))

    def _generate_checks(self):
        """Build the check set for this offer from the vacancy's check profile."""
        for offer in self:
            if offer.check_ids or not offer.vacancy_id.check_profile_id:
                continue
            lines = offer.vacancy_id.check_profile_id.line_ids
            vals_list = [{
                'offer_id': offer.id,
                'check_type_id': line.check_type_id.id,
                'level': line.level,
                'status': 'not_started' if line.is_required else 'not_required',
                'is_sensitive': line.check_type_id.is_sensitive,
            } for line in lines]
            if vals_list:
                self.env['nhs.check'].sudo().create(vals_list)

    def action_accept(self):
        self.write({'state': 'accepted'})

    def action_decline(self):
        for offer in self:
            offer.write({'state': 'declined'})
            offer.application_id.action_reject()

    def action_withdraw(self):
        self.write({'state': 'withdrawn'})

    def action_convert_unconditional(self):
        hard_gate = self.env.company.nhs_recruit_check_gate_hard
        for offer in self:
            if offer.offer_type == 'unconditional':
                continue
            if hard_gate and not offer.all_checks_cleared:
                raise UserError(_(
                    'All required pre-employment checks must be cleared before'
                    ' this offer can be made unconditional.'))
            offer.offer_type = 'unconditional'

    def action_open_onboard_wizard(self):
        self.ensure_one()
        return {
            'name': _('Confirm Hire'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.onboard.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_offer_id': self.id},
        }

    def action_view_checks(self):
        self.ensure_one()
        return {
            'name': _('Pre-Employment Checks'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.check',
            'view_mode': 'list,form',
            'domain': [('offer_id', '=', self.id)],
        }
