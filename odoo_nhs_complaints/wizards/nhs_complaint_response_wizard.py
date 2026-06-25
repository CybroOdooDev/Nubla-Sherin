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
from odoo.exceptions import UserError


class NhsComplaintResponseWizard(models.TransientModel):
    _name = 'nhs.complaint.response.wizard'
    _description = 'Complaint Response Generation and Sign-off Wizard'

    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True)
    response_text = fields.Html(string='Response Letter Body', required=True)
    sign_off_now = fields.Boolean(string='Sign Off Immediately',
                                  help='Tick to sign off the response in this step (quality lead only).')
    send_immediately = fields.Boolean(string='Send Response Immediately After Sign-off',
                                      help='Email or print the response immediately after sign-off.')
    response_method = fields.Selection([
        ('letter', 'Letter'), ('email', 'Email'),
    ], string='Send Method', default='email')

    @api.onchange('complaint_id')
    def _onchange_complaint_id(self):
        if self.complaint_id:
            self.response_text = self.complaint_id.response_text or ''

    def action_submit_for_signoff(self):
        self.ensure_one()
        complaint = self.complaint_id
        if complaint.is_third_party and complaint.consent_status in ('pending', 'refused'):
            raise UserError('Cannot submit for sign-off: consent has not been obtained for this third-party complaint.')
        complaint.with_context(nhs_workflow=True).write({
            'response_text': self.response_text,
            'state': 'awaiting_signoff',
        })
        if self.sign_off_now:
            if not self.env.user.has_group('odoo_nhs_complaints.group_nhs_complaint_quality_lead'):
                raise UserError('Only the Quality Lead or CEO delegate can sign off a response.')
            complaint.with_context(nhs_workflow=True).write({
                'signed_off_by_id': self.env.user.id,
                'signed_off_at': fields.Datetime.now(),
            })
            if self.send_immediately:
                complaint.with_context(nhs_workflow=True).write({
                    'state': 'response_sent',
                    'response_sent_at': fields.Datetime.now(),
                    'response_method': self.response_method,
                })
                template = self.env.ref('odoo_nhs_complaints.mail_template_complaint_response', raise_if_not_found=False)
                if template:
                    template.send_mail(complaint.id, force_send=False)
        return {'type': 'ir.actions.act_window_close'}
