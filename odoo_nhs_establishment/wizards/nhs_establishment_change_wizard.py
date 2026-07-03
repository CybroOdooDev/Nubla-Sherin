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

CHANGE_TYPES = [
    ('create_post', 'Create Post'),
    ('delete_post', 'Delete Post'),
    ('increase_fte', 'Increase FTE'),
    ('decrease_fte', 'Decrease FTE'),
    ('reband', 'Re-band'),
    ('transfer', 'Transfer Between Teams'),
]


class NhsEstablishmentChangeWizard(models.TransientModel):
    _name = 'nhs.establishment.change.wizard'
    _description = 'Raise an Establishment Change Request'

    change_type = fields.Selection(CHANGE_TYPES, string='Change Type', required=True,
                                    default='increase_fte')
    post_id = fields.Many2one('nhs.establishment.post', string='Affected Post')
    org_unit_id = fields.Many2one('nhs.org.unit', string='Target Unit')
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
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    reason = fields.Text(string='Reason / Business Justification', required=True)
    effective_date = fields.Date(string='Effective Date', required=True,
                                  default=fields.Date.context_today)
    submit_immediately = fields.Boolean(
        string='Submit for Approval Immediately', default=True,
        help="Untick to leave the change request in Draft for further editing.")

    @api.onchange('post_id')
    def _onchange_post_id(self):
        if self.post_id:
            self.org_unit_id = self.post_id.org_unit_id
            self.proposed_job_title = self.post_id.job_title
            self.proposed_staff_group_id = self.post_id.staff_group_id
            self.proposed_band_id = self.post_id.band_id
            self.proposed_is_medical = self.post_id.is_medical
            self.proposed_manual_indicative_salary = self.post_id.manual_indicative_salary
            self.proposed_fte = self.post_id.funded_fte
            self.proposed_headcount = self.post_id.funded_headcount
            self.proposed_contracted_hours = self.post_id.contracted_hours

    def action_create_request(self):
        self.ensure_one()
        change = self.env['nhs.establishment.change'].create({
            'change_type': self.change_type,
            'post_id': self.post_id.id if self.post_id else False,
            'org_unit_id': self.org_unit_id.id if self.org_unit_id else False,
            'proposed_job_title': self.proposed_job_title,
            'proposed_staff_group_id': self.proposed_staff_group_id.id
            if self.proposed_staff_group_id else False,
            'proposed_band_id': self.proposed_band_id.id if self.proposed_band_id else False,
            'proposed_is_medical': self.proposed_is_medical,
            'proposed_manual_indicative_salary': self.proposed_manual_indicative_salary,
            'proposed_fte': self.proposed_fte,
            'proposed_headcount': self.proposed_headcount,
            'proposed_contracted_hours': self.proposed_contracted_hours,
            'reason': self.reason,
            'effective_date': self.effective_date,
        })
        if self.submit_immediately:
            change.action_submit()
        return {
            'name': 'Establishment Change Request',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.change',
            'res_id': change.id,
            'view_mode': 'form',
            'target': 'current',
        }
