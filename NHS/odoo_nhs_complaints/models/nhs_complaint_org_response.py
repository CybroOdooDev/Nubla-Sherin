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





class NhsComplaintOrgResponse(models.Model):
    """Tracks each partner organisation's contribution to a joint complaint response."""
    _name = 'nhs.complaint.org.response'
    _description = 'Partner Organisation Joint Response Contribution'
    _order = 'org_id'
    _rec_name = 'org_id'

    complaint_id = fields.Many2one(
        'nhs.complaint', string='Complaint',
        required=True, ondelete='cascade', index=True,
    )
    org_id = fields.Many2one(
        'res.partner', string='Organisation',
        required=True,
        help='The organisation contributing to the joint response.',
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
    ], string='Status', default='pending', required=True)
    response_text = fields.Text(
        string='Response Contribution',
        help='This organisation\'s section of the joint written response.',
    )
    submitted_at = fields.Datetime(string='Submitted At', readonly=True)
    submitted_by_id = fields.Many2one(
        'res.users', string='Submitted By', readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create the org response records and add each linked organisation to the complaint's partner org list."""
        records = super().create(vals_list)
        for rec in records:
            if rec.org_id and rec.complaint_id:
                rec.complaint_id.with_context(skip_org_sync=True).write({
                    'partner_org_ids': [(4, rec.org_id.id)],
                })
        return records

    def unlink(self):
        """Delete the org response records and remove each organisation from the complaint's partner org list."""
        to_remove = [(rec.complaint_id, rec.org_id.id) for rec in self if rec.complaint_id and rec.org_id]
        result = super().unlink()
        for complaint, trust_id in to_remove:
            complaint.with_context(skip_org_sync=True).write({
                'partner_org_ids': [(3, trust_id)],
            })
        return result

    def action_submit(self):
        """Submit each organisation's response contribution, requiring response text and stamping the submission user/time."""
        for rec in self:
            if not rec.response_text:
                raise UserError(
                    f'Please enter a response contribution for '
                    f'"{rec.org_id.name}" before submitting.'
                )
            rec.write({
                'state': 'submitted',
                'submitted_at': fields.Datetime.now(),
                'submitted_by_id': self.env.user.id,
            })

    def action_reset_to_pending(self):
        """Revert each organisation's response contribution back to pending, clearing submission details."""
        for rec in self:
            rec.write({
                'state': 'pending',
                'submitted_at': False,
                'submitted_by_id': False,
            })
