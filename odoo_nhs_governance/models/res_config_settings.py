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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gov_tor_review_lead_days = fields.Integer(
        string='ToR Review Reminder (days)', default=30,
        config_parameter='odoo_nhs_governance.tor_review_lead_days',
        help='How many days before a Terms of Reference review date to raise a reminder activity.')
    gov_doi_refresh_lead_days = fields.Integer(
        string='DoI Annual Refresh Reminder (days)', default=30,
        config_parameter='odoo_nhs_governance.doi_refresh_lead_days',
        help='How many days before the annual declaration-of-interest refresh anniversary to remind members.')
    gov_action_due_lead_days = fields.Integer(
        string='Action Due Reminder (days)', default=3,
        config_parameter='odoo_nhs_governance.action_due_lead_days',
        help='How many days before an action/gap-action due date to raise an escalation warning.')
    gov_incident_risk_installed = fields.Boolean(
        string='NHS Incident & Risk Detected', compute='_compute_gov_incident_risk_installed',
        help='Whether the odoo_nhs_incident_risk module is installed. When installed, BAF principal '
             'risks can link to operational risks and corporate-tier risks are surfaced automatically.')

    def _compute_gov_incident_risk_installed(self):
        installed = bool(self.env['ir.module.module'].sudo().search_count(
            [('name', '=', 'odoo_nhs_incident_risk'), ('state', '=', 'installed')]))
        for rec in self:
            rec.gov_incident_risk_installed = installed
