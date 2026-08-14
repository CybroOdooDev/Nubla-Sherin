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

GATE_POLICIES = [
    ('hard', 'Hard Block'),
    ('soft', 'Warn Only'),
]

BOOKING_MODES = [
    ('first_come', 'First-Come'),
    ('manager_allocated', 'Manager-Allocated'),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    nhs_bank_gate_policy = fields.Selection(
        GATE_POLICIES,
        string='Compliance Gate Policy',
        default='hard',
        help="Hard block: a non-compliant member cannot be booked. Warn only: booking"
             " is allowed with a warning (officer/manager override, logged)."
    )
    nhs_bank_booking_mode = fields.Selection(
        BOOKING_MODES,
        string='Booking Mode',
        default='first_come',
        help="First-come: any eligible member who accepts is booked. Manager-allocated:"
             " the coordinator picks who is booked from those who accepted/were targeted."
    )
    nhs_bank_weekly_hours_limit = fields.Float(
        string='Safe Weekly Hours Limit',
        default=48.0,
        help="Default safe/legal weekly hours limit (substantive + bank), per the"
             " Working Time Regulations. Overridable per member."
    )
    nhs_bank_offer_expiry_hours = fields.Integer(
        string='Offer Expiry (Hours)',
        default=24,
        help="Default hours before a pending shift offer auto-expires if not"
             " responded to."
    )
    nhs_bank_agency_comparator_pct = fields.Float(
        string='Agency Comparator Uplift (%)',
        default=30.0,
        help="Indicative % an equivalent agency shift would cost above the bank rate,"
             " used to estimate cost avoidance where an actual agency cost has not"
             " been captured."
    )
    nhs_bank_digest_recipients = fields.Char(
        string='Coordinator Digest Recipients',
        help="Comma-separated fallback email addresses for the bank coordinator digest."
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhs_bank_gate_policy = fields.Selection(
        related='company_id.nhs_bank_gate_policy', readonly=False)
    nhs_bank_booking_mode = fields.Selection(
        related='company_id.nhs_bank_booking_mode', readonly=False)
    nhs_bank_weekly_hours_limit = fields.Float(
        related='company_id.nhs_bank_weekly_hours_limit', readonly=False)
    nhs_bank_offer_expiry_hours = fields.Integer(
        related='company_id.nhs_bank_offer_expiry_hours', readonly=False)
    nhs_bank_agency_comparator_pct = fields.Float(
        related='company_id.nhs_bank_agency_comparator_pct', readonly=False)
    nhs_bank_digest_recipients = fields.Char(
        related='company_id.nhs_bank_digest_recipients', readonly=False)
