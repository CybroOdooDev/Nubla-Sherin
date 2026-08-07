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
from odoo.exceptions import UserError


class NhsComplaintResponseWizard(models.TransientModel):
    """Wizard to draft, preview, sign off, and send a complaint's formal written response."""
    _name = 'nhs.complaint.response.wizard'
    _description = 'Complaint Response Generation and Sign-off Wizard'

    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True)
    response_text = fields.Html(string='Response Letter Body')
    sign_off_now = fields.Boolean(string='Sign Off Immediately',
                                  help='Tick to sign off the response in this step (quality lead only).')
    send_immediately = fields.Boolean(string='Send Response Immediately After Sign-off',
                                      help='Email or print the response immediately after sign-off.')
    response_method = fields.Selection([
        ('letter', 'Letter'), ('email', 'Email'),
    ], string='Send Method', default='email')

    points_of_complaint = fields.Text(
        string='Points of Complaint',
        related='complaint_id.investigation_id.points_of_complaint',
        readonly=True,
    )
    findings = fields.Text(
        string='Investigation Findings',
        related='complaint_id.investigation_id.findings',
        readonly=True,
    )

    @api.onchange('complaint_id')
    def _onchange_complaint_id(self):
        """Pre-fill the response letter body with the complaint's existing draft response text."""
        if self.complaint_id:
            self.response_text = self.complaint_id.response_text or ''

    def _check_response_text(self):
        """Raise if the response letter body is blank (handles empty HTML like <p><br></p>)."""
        import re
        text = self.response_text or ''
        if not re.sub(r'<[^>]+>', '', text).strip():
            raise UserError('Please enter a response letter before proceeding.')

    def action_save_draft(self):
        """Save the entered response text onto the complaint and move it to the Response Draft state."""
        self.ensure_one()
        self._check_response_text()
        self.complaint_id.with_context(nhs_workflow=True).write({
            'response_text': self.response_text,
            'state': 'response_draft',
        })
        return {'type': 'ir.actions.act_window_close'}

    def action_preview(self):
        """Save the response text onto the complaint and open a printable preview of the response letter report."""
        self.ensure_one()
        self._check_response_text()
        self.complaint_id.with_context(nhs_workflow=True).write({
            'response_text': self.response_text,
        })
        return self.env.ref('odoo_nhs_complaints.action_report_nhs_complaint_response').report_action(self.complaint_id)

    def action_submit_for_signoff(self):
        """Save the response text, submit the complaint for sign-off, and optionally sign off and send it immediately."""
        self.ensure_one()
        self._check_response_text()
        complaint = self.complaint_id
        if complaint.is_third_party and complaint.consent_status in ('pending', 'refused'):
            raise UserError('Cannot submit for sign-off: consent has not been obtained for this third-party complaint.')
        
        # Save response_text first
        complaint.with_context(nhs_workflow=True).write({
            'response_text': self.response_text,
        })

        if self.sign_off_now:
            if not self.env.user.has_group('odoo_nhs_complaints.group_nhs_complaint_quality_lead'):
                raise UserError('Only the Quality Lead or CEO delegate can sign off a response.')
            
            # Submit for sign-off (performs validation like multi-org response check)
            complaint.action_submit_for_signoff()

            complaint.action_sign_off()
            
            if self.send_immediately:
                complaint.write({'response_method': self.response_method})
                complaint.action_send_response()
        else:
            complaint.action_submit_for_signoff()
            
        return {'type': 'ir.actions.act_window_close'}
