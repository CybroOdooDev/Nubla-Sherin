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


class NhsOnboardWizard(models.TransientModel):
    """Confirms a hire: sets the start date once checks are cleared,
    increments the funded post's in-post FTE in the Establishment Register,
    closes the vacancy, and optionally creates a workforce-member record in
    odoo_nhs_training so mandatory-training requirements attach from day one."""
    _name = 'nhs.onboard.wizard'
    _description = 'Onboarding handoff wizard'

    offer_id = fields.Many2one('nhs.offer', string='Offer', required=True)
    candidate_id = fields.Many2one(
        related='offer_id.candidate_id', string='Candidate', readonly=True)
    vacancy_id = fields.Many2one(
        related='offer_id.vacancy_id', string='Vacancy', readonly=True)
    all_checks_cleared = fields.Boolean(
        related='offer_id.all_checks_cleared', readonly=True)
    start_date = fields.Date(string='Start Date', required=True)
    create_training_member = fields.Boolean(
        string='Create Workforce Member in Training Module', default=True,
        help="If the NHS Mandatory Training module is installed, create a workforce-member"
             " record so training requirements attach from the start date.")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        offer_id = res.get('offer_id') or self.env.context.get('default_offer_id')
        if offer_id:
            offer = self.env['nhs.offer'].browse(offer_id)
            res['start_date'] = offer.start_date or fields.Date.context_today(self)
        return res

    def action_confirm_hire(self):
        self.ensure_one()
        offer = self.offer_id
        hard_gate = self.env.company.nhs_recruit_check_gate_hard
        if hard_gate and not offer.all_checks_cleared:
            raise UserError(_(
                'All required pre-employment checks must be cleared before the'
                ' hire can be confirmed.'))

        offer.write({
            'state': 'accepted',
            'offer_type': 'unconditional',
            'start_date': self.start_date,
        })
        offer.application_id.write({'stage': 'hired'})

        post = offer.vacancy_id.post_id
        post.write({'in_post_fte': post.in_post_fte + offer.vacancy_id.fte})

        if self.create_training_member and 'nhs.workforce.member' in self.env:
            self.env['nhs.workforce.member'].create({
                'name': offer.candidate_id.name,
                'email': offer.candidate_id.email,
                'post_id': post.id,
                'start_date': self.start_date,
            })

        offer.vacancy_id.action_mark_filled()
        offer.vacancy_id.action_close()
        return {'type': 'ir.actions.act_window_close'}
