# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_nhs_board_member = fields.Boolean(string='Is NHS Board Member', default=False, index=True)
    nhs_trust_id = fields.Many2one('nhs.trust', string='NHS Trust', index=True)
    nhs_board_role = fields.Selection([
        ('chair', 'Chair'),
        ('ceo', 'Chief Executive Officer (CEO)'),
        ('medical_director', 'Medical Director'),
        ('nursing_director', 'Director of Nursing'),
        ('finance_director', 'Director of Finance'),
        ('exec', 'Executive Director'),
        ('non_exec', 'Non-Executive Director'),
        ('other', 'Other Board Member'),
    ], string='Board Role', index=True)
    is_voting_member = fields.Boolean(string='Voting Member', default=True)
    term_start_date = fields.Date(string='Term Start Date')
    term_end_date = fields.Date(string='Term End Date')
    appointment_authority = fields.Char(string='Appointment Authority', help='e.g., NHS England, Scottish Government, etc.')
    is_term_active = fields.Boolean(string='Term Active', compute='_compute_is_term_active', store=True, index=True)

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
