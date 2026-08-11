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
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class NhsCandidate(models.Model):
    """A recruitment candidate — deliberately minimal (identity/contact and
    process data only). Sensitive check data lives on nhs.check with
    restricted access, not here."""
    _name = 'nhs.candidate'
    _inherit = ['mail.thread']
    _description = 'A recruitment candidate (data-minimised)'
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Candidate reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    is_internal = fields.Boolean(
        string='Internal Candidate',
        help="Existing staff member applying internally."
    )
    application_ids = fields.One2many(
        'nhs.application',
        'candidate_id',
        string='Applications',
    )
    application_count = fields.Integer(
        string='Application Count',
        compute='_compute_application_count',
    )
    talent_pool_consent = fields.Boolean(
        string='Talent Pool Consent',
        tracking=True,
        help="Candidate has consented to being retained for consideration"
             " against future vacancies, overriding the normal purge."
    )
    retention_expiry = fields.Date(
        string='Retention Expiry',
        compute='_compute_retention_expiry',
        store=True,
        help="When this candidate's personal data is due for anonymisation/purge,"
             " for unsuccessful applicants without talent-pool consent."
    )
    is_anonymised = fields.Boolean(
        string='Anonymised',
        readonly=True,
        help="Personal data on this record has been purged by the retention cron."
    )
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Assign the next 'nhs.candidate' sequence number when none is
        supplied."""
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.candidate') or 'New'
        return super().create(vals_list)

    def _compute_application_count(self):
        """Count the candidate's applications."""
        for candidate in self:
            candidate.application_count = len(candidate.application_ids)

    @api.depends('application_ids.stage', 'application_ids.decision_date', 'talent_pool_consent',
                 'company_id.nhs_recruit_retention_months')
    def _compute_retention_expiry(self):
        """Set the anonymisation due date to the latest unsuccessful
        decision date plus the company's retention period (default 24
        months) for candidates who were never hired and have not given
        talent-pool consent; otherwise leave it unset."""
        for candidate in self:
            if candidate.talent_pool_consent:
                candidate.retention_expiry = False
                continue
            unsuccessful = candidate.application_ids.filtered(
                lambda a: a.stage in ('rejected', 'not_shortlisted', 'withdrawn')
                and a.decision_date
            )
            if unsuccessful and not candidate.application_ids.filtered(
                    lambda a: a.stage == 'hired'):
                months = candidate.company_id.nhs_recruit_retention_months or 24
                latest_decision = max(unsuccessful.mapped('decision_date'))
                candidate.retention_expiry = latest_decision + relativedelta(months=months)
            else:
                candidate.retention_expiry = False

    def _anonymise(self):
        """Irreversibly scrub personal data, keeping the record (and any
        aggregate equality-monitoring stats) for de-identified reporting.
        Only 'name' varies per candidate (it embeds the reference), so that's
        the sole per-record write; everything else is identical across the
        whole batch and is written once."""
        for candidate in self:
            candidate.with_context(mail_notrack=True).write({
                'name': f'Anonymised Candidate {candidate.reference}',
            })
        self.with_context(mail_notrack=True).write({
            'email': False,
            'phone': False,
            'is_anonymised': True,
            'active': False,
        })
        self.mapped('application_ids').write({
            'supporting_statement': False,
            'employment_history': False,
        })

    @api.model
    def _cron_purge_retention(self):
        """Anonymise unsuccessful applicants past their retention expiry and
        without talent-pool consent."""
        today = fields.Date.context_today(self)
        candidates = self.search([
            ('retention_expiry', '<=', today),
            ('talent_pool_consent', '=', False),
            ('is_anonymised', '=', False),
        ])
        candidates._anonymise()
