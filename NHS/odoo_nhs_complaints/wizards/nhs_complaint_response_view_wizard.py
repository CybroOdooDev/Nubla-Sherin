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


class NhsComplaintResponseViewWizard(models.TransientModel):
    """Read-only wizard displaying a complaint's sign-off and sent-response details."""
    _name = 'nhs.complaint.response.view.wizard'
    _description = 'Complaint Response Details'

    complaint_id = fields.Many2one('nhs.complaint', required=True)
    signed_off_by_id = fields.Many2one(
        'res.users', related='complaint_id.signed_off_by_id', string='Signed Off By')
    signed_off_at = fields.Datetime(
        related='complaint_id.signed_off_at', string='Signed Off At')
    response_sent_at = fields.Datetime(
        related='complaint_id.response_sent_at', string='Response Sent At')
    response_method = fields.Selection(
        related='complaint_id.response_method', string='Response Method')
    response_text = fields.Html(
        related='complaint_id.response_text', string='Response Letter')
