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


class NhsCheck(models.Model):
    """One NHS Employment Check Standard check on a candidate. Access is
    restricted to the Pre-Employment Checks role and Recruitment Manager —
    not general recruitment officers or panels."""
    _name = 'nhs.check'
    _inherit = ['mail.thread']
    _description = 'An NHS Employment Check Standard check on a candidate (restricted access)'
    _order = 'id'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    offer_id = fields.Many2one(
        'nhs.offer', string='Offer', required=True, ondelete='cascade', index=True)
    candidate_id = fields.Many2one(
        related='offer_id.candidate_id', string='Candidate', store=True, readonly=True)
    company_id = fields.Many2one(
        related='offer_id.company_id', string='Company', store=True, readonly=True)
    check_type_id = fields.Many2one('nhs.check.type', string='Check Type', required=True)
    level = fields.Selection([
        ('standard', 'Standard'),
        ('enhanced', 'Enhanced'),
        ('enhanced_barred', 'Enhanced with Barred List'),
    ], string='Level')
    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('cleared', 'Cleared'),
        ('concern', 'Concern'),
        ('not_required', 'Not Required'),
    ], string='Status', default='not_started', required=True, tracking=True)
    verified_by_id = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Date(string='Verified Date', readonly=True)
    expiry_date = fields.Date(
        string='Expiry Date',
        help="For time-limited checks (e.g. right to work), for later re-check."
    )
    reference_number = fields.Char(
        string='Reference Number', help="e.g. DBS certificate number, registration PIN.")
    detail = fields.Text(string='Detail (Sensitive)')
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence')
    is_sensitive = fields.Boolean(
        string='Sensitive',
        help="Health/criminal-record data — flags heightened-restriction records."
    )
    active = fields.Boolean(string='Active', default=True)

    @api.depends('check_type_id.name', 'candidate_id.name')
    def _compute_name(self):
        for check in self:
            if check.check_type_id and check.candidate_id:
                check.name = f"{check.check_type_id.name} — {check.candidate_id.name}"
            else:
                check.name = check.check_type_id.name or ('New Check')

    def action_mark_in_progress(self):
        self.write({'status': 'in_progress'})

    def action_mark_cleared(self):
        today = fields.Date.context_today(self)
        self.write({
            'status': 'cleared',
            'verified_by_id': self.env.user.id,
            'verified_date': today,
        })

    def action_mark_concern(self):
        self.write({'status': 'concern'})

    def action_mark_not_required(self):
        self.write({
            'status': 'not_required',
            'verified_by_id': False,
            'verified_date': False,
        })

    @api.model
    def _cron_check_expiring(self, lead_days=60):
        """Nudge followers on checks whose expiry (e.g. right-to-work) is approaching."""
        today = fields.Date.context_today(self)
        checks = self.search([
            ('expiry_date', '!=', False),
            ('status', '=', 'cleared'),
        ])
        for check in checks:
            days_left = (check.expiry_date - today).days
            if 0 <= days_left <= lead_days and days_left % 15 == 0:
                check.message_post(
                    body=("%(check)s for %(candidate)s expires in %(days)d day(s).") % {
                        'check': check.check_type_id.name,
                        'candidate': check.candidate_id.name,
                        'days': days_left,
                    })
