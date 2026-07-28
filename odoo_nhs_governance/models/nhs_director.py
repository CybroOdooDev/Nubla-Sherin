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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import timedelta
from odoo import api, fields, models


class NhsDirector(models.Model):
    _name = 'nhs.director'
    _description = 'Director / Officer (light appointment & FPPR register)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True, help='Director/officer name.')
    role_title = fields.Selection([
        ('chair', 'Chair'),
        ('ceo', 'Chief Executive Officer (CEO)'),
        ('medical_director', 'Medical Director'),
        ('director_of_nursing', 'Director of Nursing'),
        ('director_of_finance', 'Director of Finance'),
        ('executive_director', 'Executive Director'),
        ('non_executive_director', 'Non-Executive Director'),
        ('other', 'Other Board Member'),
    ], tracking=True, help='Board role.')
    is_executive = fields.Boolean(tracking=True, help='Executive vs non-executive director.')
    appointment_date = fields.Date(tracking=True, help='Date first appointed to the board.')
    term_end = fields.Date(tracking=True, help='Term end date, if fixed.')
    fppr_status = fields.Selection([
        ('not_checked', 'Not Checked'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('concern', 'Concern Raised'),
    ], default='not_checked', tracking=True,
       help='Fit and Proper Person Requirement check status. Directors are subject to the FPPR '
            '(CQC/NHS requirement) — the organisation must assure itself directors are fit for role.')
    fppr_check_date = fields.Date(tracking=True, help='Date of the last Fit and Proper Person check.')
    partner_id = fields.Many2one(
        'res.partner', string='Contact',
        help='Optional link to a Contact record, e.g. for correspondence.')
    user_id = fields.Many2one(
        'res.users', string='User',
        help='Optional system user link, used to grant portal/system access to this director '
             'for their own packs, actions and declarations.')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 help='Owning company; record rules scope on it.')
    active = fields.Boolean(default=True, help='Archive flag.')
    committee_membership_ids = fields.One2many(
        'nhs.committee.member', 'director_id', string='Committee Memberships',
        help='Committees this director sits on.')
    committee_count = fields.Integer(string='Committee Count', compute='_compute_counts',
                                     help='Number of committees this director currently sits on.')
    declaration_ids = fields.One2many(
        'nhs.declaration', 'director_id', string='Declarations Of Interest',
        help='This director\'s declarations of interest.')
    declaration_count = fields.Integer(string='Declaration Count', compute='_compute_counts',
                                       help='Number of declarations of interest recorded for this director.')

    @api.depends('committee_membership_ids', 'declaration_ids')
    def _compute_counts(self):
        """Compute committee membership and declaration counts shown on smart buttons."""
        for rec in self:
            rec.committee_count = len(rec.committee_membership_ids)
            rec.declaration_count = len(rec.declaration_ids)

    def action_view_committees(self):
        """Open the list of committee memberships held by this director."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Committee Memberships',
            'res_model': 'nhs.committee.member',
            'view_mode': 'list,form',
            'domain': [('director_id', '=', self.id)],
        }

    def action_view_declarations(self):
        """Open the list of declarations of interest recorded for this director."""
        self.ensure_one()
        context = {'default_director_id': self.id}
        if not self.declaration_ids:
            context['default_event'] = 'appointment'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Declarations of Interest',
            'res_model': 'nhs.declaration',
            'view_mode': 'list,form',
            'views': [(self.env.ref('odoo_nhs_governance.view_nhs_declaration_list').id, 'list'), (False, 'form')],
            'domain': [('director_id', '=', self.id)],
            'context': context,
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Create directors and schedule an appointment declaration activity for each."""
        directors = super().create(vals_list)
        for director in directors:
            director.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=director.user_id.id or self.env.user.id,
                note=f'New director appointed: Please complete the "On Appointment" declaration '
                     f'of interest for {director.name}.'
            )
        return directors

    @api.model
    def _cron_doi_annual_refresh_reminder(self):
        """Annual declaration-of-interest refresh reminder: schedule an activity for any
        director who has not made a declaration (including a nil return) in the last 365 days."""
        lead_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_governance.doi_refresh_lead_days', 30))
        cutoff = fields.Date.today() - timedelta(days=365 - lead_days)
        directors = self.search([('committee_membership_ids', '!=', False)])
        for director in directors:
            last_declaration = director.declaration_ids.filtered(
                lambda d: d.event in ('appointment', 'annual')).sorted('date_from', reverse=True)[:1]
            if not last_declaration or (last_declaration.date_from and last_declaration.date_from <= cutoff):
                director.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=director.user_id.id or self.env.user.id,
                    note=f'Annual declaration of interest refresh due for {director.name}.')
