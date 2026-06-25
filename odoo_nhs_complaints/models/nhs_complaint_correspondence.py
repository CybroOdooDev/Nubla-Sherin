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
from odoo import fields, models
from odoo.exceptions import UserError


class NhsComplaintCorrespondence(models.Model):
    _name = 'nhs.complaint.correspondence'
    _description = 'Complaint Correspondence Log Entry'
    _order = 'occurred_at desc'

    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True,
                                   ondelete='cascade')
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Direction', required=True,
       help='Inbound: received from complainant. Outbound: sent by the organisation.')
    channel = fields.Selection([
        ('letter', 'Letter'),
        ('email', 'Email'),
        ('phone', 'Phone Call'),
        ('in_person', 'In Person'),
    ], string='Channel', required=True)
    correspondence_type = fields.Selection([
        ('acknowledgement', 'Acknowledgement'),
        ('holding', 'Holding Letter'),
        ('response', 'Formal Response'),
        ('closure', 'Closure'),
        ('consent_request', 'Consent Request'),
        ('general', 'General'),
    ], string='Type', default='general')
    occurred_at = fields.Datetime(string='Date / Time', required=True,
                                  default=fields.Datetime.now)
    summary = fields.Text(string='Summary / Content', required=True,
                          help='What was said or sent.')
    user_id = fields.Many2one('res.users', string='Handled By',
                              default=lambda self: self.env.user)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                      help='Letters, emails or other documents.')
    company_id = fields.Many2one('res.company', string='Organisation',
                                 related='complaint_id.company_id', store=True)

    def unlink(self):
        raise UserError(
            'Correspondence log entries are statutory records and cannot be deleted.'
        )
