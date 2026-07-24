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
from datetime import timedelta
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    nhs_gov_fppr_status = fields.Selection([
        ('not_checked', 'Not Checked'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('concern', 'Concern Raised'),
    ], string='FPPR Status', default='not_checked', tracking=True,
       help='Fit and Proper Person Requirement check status. Directors are subject to the FPPR '
            '(CQC/NHS requirement) — the organisation must assure itself directors are fit for role.')
    nhs_gov_fppr_check_date = fields.Date(string='FPPR Check Date', tracking=True,
                                          help='Date of the last Fit and Proper Person check.')
    nhs_gov_committee_membership_ids = fields.One2many(
        'nhs.committee.member', 'partner_id', string='Committee Memberships',
        help='Committees this person sits on.')
    nhs_gov_committee_count = fields.Integer(string='Committee Count', compute='_compute_nhs_gov_counts')
    nhs_gov_declaration_ids = fields.One2many(
        'nhs.declaration', 'partner_id', string='Declarations Of Interest',
        help='Their declarations of interest.')
    nhs_gov_declaration_count = fields.Integer(string='Declaration Count', compute='_compute_nhs_gov_counts')
    nhs_is_executive = fields.Boolean(
        string='Executive',
        tracking=True,
        help='Executive vs non-executive director (used for Board balance and FPPR).'
    )

    @api.depends('nhs_gov_committee_membership_ids', 'nhs_gov_declaration_ids')
    def _compute_nhs_gov_counts(self):
        for rec in self:
            rec.nhs_gov_committee_count = len(rec.nhs_gov_committee_membership_ids)
            rec.nhs_gov_declaration_count = len(rec.nhs_gov_declaration_ids)

    def action_view_nhs_gov_committees(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Committee Memberships',
            'res_model': 'nhs.committee.member',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_view_nhs_gov_declarations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Declarations of Interest',
            'res_model': 'nhs.declaration',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    @api.model
    def _cron_doi_annual_refresh_reminder(self):
        """Annual declaration-of-interest refresh reminder: schedule an activity for any
        committee member who has not made a declaration (including a nil return) in the
        last 365 days."""
        lead_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_governance.doi_refresh_lead_days', 30))
        cutoff = fields.Date.today() - timedelta(days=365 - lead_days)
        partners = self.search([('nhs_gov_committee_membership_ids', '!=', False)])
        for partner in partners:
            last_declaration = partner.nhs_gov_declaration_ids.filtered(
                lambda d: d.event in ('appointment', 'annual')).sorted('date_from', reverse=True)[:1]
            if not last_declaration or (last_declaration.date_from and last_declaration.date_from <= cutoff):
                partner.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=partner.user_ids[:1].id or self.env.user.id,
                    note=f'Annual declaration of interest refresh due for {partner.name}.')
