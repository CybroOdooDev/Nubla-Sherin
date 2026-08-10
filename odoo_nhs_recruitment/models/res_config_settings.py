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
import uuid
from odoo import api, fields, models


class ResCompany(models.Model):
    """Per-company NHS recruitment parameters: approval stages, the
    pre-employment-check gating policy, retention period, and the public
    application-form token."""
    _inherit = 'res.company'

    nhs_recruit_workforce_approval_required = fields.Boolean(
        string='Require Workforce Approval', default=True,
        help="A vacancy must be workforce-approved before it can proceed to finance approval.")
    nhs_recruit_finance_approval_required = fields.Boolean(
        string='Require Finance Approval', default=True,
        help="A vacancy must be finance-approved before it can be opened for advertising.")
    nhs_recruit_check_gate_hard = fields.Boolean(
        string='Hard Gate on Pre-Employment Checks', default=True,
        help="When enabled, an offer cannot be made unconditional (and a candidate cannot"
             " start) until every required check is cleared. When disabled, this is a"
             " soft/advisory gate only.")
    nhs_recruit_retention_months = fields.Integer(
        string='Unsuccessful-Applicant Retention (Months)', default=24,
        help="How long an unsuccessful applicant's personal data is retained before"
             " automatic anonymisation, unless they have consented to the talent pool.")
    nhs_recruit_public_form_enabled = fields.Boolean(
        string='Enable Public Application Form', default=False)
    nhs_recruit_public_form_token = fields.Char(
        string='Public Application Form Token', copy=False,
        help="Secret token in the public application form URL: /jobs/apply/<token>.")
    nhs_recruit_public_form_url = fields.Char(
        string='Public Application Form URL', compute='_compute_nhs_recruit_public_form_url',
        help="Full link to the public vacancy list, ready to publish or share.")

    @api.depends('nhs_recruit_public_form_enabled', 'nhs_recruit_public_form_token')
    def _compute_nhs_recruit_public_form_url(self):
        """Build the public vacancy-list URL from the base URL and token, or
        clear it if the public form is disabled or has no token yet."""
        for company in self:
            if company.nhs_recruit_public_form_enabled and company.nhs_recruit_public_form_token:
                company.nhs_recruit_public_form_url = '%s/jobs/apply/%s' % (
                    company.get_base_url(), company.nhs_recruit_public_form_token)
            else:
                company.nhs_recruit_public_form_url = False

    def _nhs_recruit_generate_token(self):
        """Issue a fresh random token, invalidating any previously shared
        public application-form link."""
        for company in self:
            company.nhs_recruit_public_form_token = uuid.uuid4().hex


class ResConfigSettings(models.TransientModel):
    """Exposes the NHS recruitment company parameters on the Settings screen."""
    _inherit = 'res.config.settings'

    nhs_recruit_workforce_approval_required = fields.Boolean(
        related='company_id.nhs_recruit_workforce_approval_required', readonly=False)
    nhs_recruit_finance_approval_required = fields.Boolean(
        related='company_id.nhs_recruit_finance_approval_required', readonly=False)
    nhs_recruit_check_gate_hard = fields.Boolean(
        related='company_id.nhs_recruit_check_gate_hard', readonly=False)
    nhs_recruit_retention_months = fields.Integer(
        related='company_id.nhs_recruit_retention_months', readonly=False)
    nhs_recruit_public_form_enabled = fields.Boolean(
        related='company_id.nhs_recruit_public_form_enabled', readonly=False)
    nhs_recruit_public_form_token = fields.Char(
        related='company_id.nhs_recruit_public_form_token', readonly=True)
    nhs_recruit_public_form_url = fields.Char(
        related='company_id.nhs_recruit_public_form_url', readonly=True)

    def action_nhs_recruit_generate_token(self):
        """Regenerate the company's public form token and reload the settings
        page so the new URL is displayed."""
        self.company_id._nhs_recruit_generate_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_nhs_recruit_open_form(self):
        """Open the public application form URL in a new tab, or reload the
        page if no URL is available yet."""
        self.ensure_one()
        if not self.nhs_recruit_public_form_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {
            'type': 'ir.actions.act_url',
            'url': self.nhs_recruit_public_form_url,
            'target': 'new',
        }
