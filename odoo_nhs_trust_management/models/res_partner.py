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
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_nhs_board_member = fields.Boolean(
        string='NHS Board Member',
        default=False, 
        index=True,
        help="Master flag. Setting to True reveals the NHS Board Member notebook page on the partner form. Used in domain filters across all NHS views."
    )
    nhs_trust_id = fields.Many2one(
        'nhs.trust', 
        string='NHS Trust', 
        index=True,
        help="Trust this person sits on the board of. Required if is_nhs_board_member=True (enforced by view)."
    )
    nhs_board_role = fields.Selection([
        ('chair', 'Chair'),
        ('ceo', 'Chief Executive Officer (CEO)'),
        ('medical_director', 'Medical Director'),
        ('nursing_director', 'Director of Nursing'),
        ('finance_director', 'Director of Finance'),
        ('exec', 'Executive Director'),
        ('non_exec', 'Non-Executive Director'),
        ('other', 'Other Board Member'),
    ], 
        string='Board Role', 
        index=True,
        help="Selection: chair / vice_chair / ceo / medical_director / director_of_nursing / "
             "finance_director / coo / exec_director / ned / associate_ned / governor / other."
             " NED = Non-Executive Director (independent oversight role)."
    )
    is_voting_member = fields.Boolean(
        string='Voting Member', 
        default=True,
        help="True for full voting board members. Default: True. Set False for advisors, observers, associate directors."
    )
    term_start_date = fields.Date(
        string='Term Start Date',
        help="Start of current appointment term."
    )
    term_end_date = fields.Date(
        string='Term End Date',
        help="End of current appointment term. Used to compute is_term_active."
    )
    appointment_authority = fields.Char(
        string='Appointment Authority', 
        help="Body that appointed this member (e.g. 'NHS Improvement', 'Council of Governors', 'Secretary of State')."
    )
    is_term_active = fields.Boolean(
        string='Term Active', 
        compute='_compute_is_term_active', 
        store=True, 
        index=True,
        help="True if today's date is within [term_start_date, term_end_date]."
    )


    @api.depends('term_start_date', 'term_end_date', 'is_nhs_board_member')
    def _compute_is_term_active(self):
        today = fields.Date.context_today(self)
        for partner in self:
            if not partner.is_nhs_board_member:
                partner.is_term_active = False
                continue
            start = partner.term_start_date
            end = partner.term_end_date
            if start and end:
                partner.is_term_active = start <= today <= end
            elif start:
                partner.is_term_active = start <= today
            elif end:
                partner.is_term_active = today <= end
            else:
                partner.is_term_active = True
