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
#############################################################################
from odoo import api, fields, models


class NhsComplaintPhso(models.Model):
    _name = 'nhs.complaint.phso'
    _description = 'PHSO Escalation Stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'referred_at desc'
    _rec_name = 'phso_reference'

    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True,
                                   ondelete='restrict',
                                   help='The complaint referred to the Parliamentary and Health Service Ombudsman.')
    referred_at = fields.Date(string='Date Referred', required=True,
                              help='Date the complaint was referred to the PHSO.')
    phso_reference = fields.Char(string='PHSO Case Reference',
                                 help='The reference number assigned by the PHSO.')
    state = fields.Selection([
        ('referred', 'Referred'),
        ('under_review', 'Under Review'),
        ('decision_made', 'Decision Made'),
        ('closed', 'Closed'),
    ], string='PHSO Status', required=True, default='referred', tracking=True)
    outcome = fields.Selection([
        ('not_upheld', 'Not Upheld'),
        ('partly_upheld', 'Partly Upheld'),
        ('upheld', 'Upheld'),
    ], string='Outcome', tracking=True,
       help='The PHSO decision on the complaint.')
    recommendations = fields.Text(string='PHSO Recommendations',
                                  help='Recommendations issued by the PHSO.')
    action_ids = fields.One2many('nhs.action', 'phso_id', string='Actions from Recommendations',
                                 help='Corrective actions arising from PHSO recommendations.')
    compensation_recommended = fields.Monetary(string='Compensation Recommended',
                                               currency_field='currency_id',
                                               help='Financial remedy recommended by the PHSO (rare).')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Organisation',
                                 related='complaint_id.company_id', store=True)

    def unlink(self):
        raise UserError(
            'PHSO escalation records are statutory and cannot be deleted.'
        )

    def action_mark_under_review(self):
        self.write({'state': 'under_review'})

    def action_record_decision(self):
        self.write({'state': 'decision_made'})

    def action_close(self):
        self.write({'state': 'closed'})

    @api.model
    def _cron_phso_followup(self):
        open_phsos = self.search([('state', 'in', ('referred', 'under_review'))])
        for phso in open_phsos:
            phso.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=phso.complaint_id.handler_id.id if phso.complaint_id.handler_id else self.env.user.id,
                note=f'PHSO case {phso.phso_reference or phso.id} has had no progress update this week.',
            )
