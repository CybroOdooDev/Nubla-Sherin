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


class NhsCqcNotification(models.Model):
    """Extends nhs.cqc.notification with a direct link to a CQC Inspection
    record from odoo_nhs_trust_operations. This lives in the bridge because
    nhs.cqc.notification (incident module) must not reference
    nhs.trust.cqc.inspection (trust operations module) directly."""
    _inherit = 'nhs.cqc.notification'

    cqc_inspection_id = fields.Many2one(
        'nhs.trust.cqc.inspection',
        string='Linked CQC Inspection',
        ondelete='set null',
        help='The CQC inspection where this notification was reviewed or '
             'referenced as evidence. Filtered to inspections for this '
             'incident\'s trust.',
    )
    trust_id = fields.Many2one(
        'nhs.trust',
        related='incident_id.trust_id',
        string='Trust',
        store=False,
        help='Derived from the incident\'s linked trust. Used to scope the '
             'CQC inspection picker to the correct trust.',
    )
