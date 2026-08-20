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

GATE_POLICIES = [
    ('hard', 'Hard Block'),
    ('soft', 'Warn Only'),
]

BOOKING_MODES = [
    ('first_come', 'First-Come'),
    ('manager_allocated', 'Manager-Allocated'),
]


def _digest_recipient_domain(users):
    """Only Bank Officers/Managers are selectable as digest recipients.
    Defined as a callable (not an XML domain) because it needs env.ref() —
    ref() isn't available in a view-level field domain expression."""
    env = users.env
    officer = env.ref('odoo_nhs_staff_bank.group_nhs_bank_officer', raise_if_not_found=False)
    manager = env.ref('odoo_nhs_staff_bank.group_nhs_bank_manager', raise_if_not_found=False)
    group_ids = [group.id for group in (officer, manager) if group]
    return [('group_ids', 'in', group_ids)] if group_ids else [('id', '=', False)]


class ResCompany(models.Model):
    """Company-level settings for the NHS Staff Bank: the compliance gate
    policy, booking mode, safe working-hours limit, offer expiry, agency
    comparator uplift and digest recipients."""
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
    nhs_bank_digest_recipient_ids = fields.Many2many(
        'res.users',
        'nhs_bank_digest_recipient_rel',
        'company_id',
        'user_id',
        string='Coordinator Digest Recipients',
        domain=_digest_recipient_domain,
        help="Pick which Bank Officers/Managers should receive the daily digest of"
             " open/urgent shifts. Only they get it — no one else, automatically."
    )
    nhs_bank_auto_create_portal_user = fields.Boolean(
        string='Auto-Create Portal User on Member Creation',
        help="When a new bank member is created with an email address set (and no"
             " portal user already linked), automatically create their portal"
             " account and send the invitation — instead of an admin having to"
             " click 'Create Portal User' on every member by hand."
    )
    nhs_bank_digest_shift_ids = fields.Many2many(
        'nhs.bank.shift',
        compute='_compute_nhs_bank_digest_shift_ids',
        string='Open/Urgent Shifts (Digest)',
        help="This company's currently open/partially-filled shifts — the"
             " content of the daily coordinator digest."
    )
    nhs_bank_digest_open_count = fields.Integer(
        compute='_compute_nhs_bank_digest_shift_ids', string='Open Shifts (Digest)')
    nhs_bank_digest_urgent_count = fields.Integer(
        compute='_compute_nhs_bank_digest_shift_ids', string='Urgent Shifts (Digest)')
    nhs_bank_digest_noncompliant_member_ids = fields.Many2many(
        'nhs.bank.member',
        compute='_compute_nhs_bank_digest_shift_ids',
        string='Non-Compliant Members (Digest)',
        help="Active members currently non-compliant — folded into the daily"
             " digest instead of a separate real-time alert."
    )

    @api.depends()
    def _compute_nhs_bank_digest_shift_ids(self):
        # No field dependency: this is a live cross-model search (current
        # open/partially-filled shifts), always (re)computed on access rather
        # than cached against some other field's change.
        for company in self:
            shifts = self.env['nhs.bank.shift'].search([
                ('company_id', '=', company.id),
                ('state', 'in', ('open', 'partially_filled')),
            ])
            company.nhs_bank_digest_shift_ids = shifts
            company.nhs_bank_digest_open_count = len(shifts)
            company.nhs_bank_digest_urgent_count = len(
                shifts.filtered(lambda s: s.urgency in ('urgent', 'last_minute')))
            company.nhs_bank_digest_noncompliant_member_ids = self.env['nhs.bank.member'].search([
                ('company_id', '=', company.id),
                ('state', '=', 'active'),
                ('compliance_status', '=', 'non_compliant'),
            ])


class ResConfigSettings(models.TransientModel):
    """Exposes the NHS Staff Bank company settings on the Settings screen."""
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
    nhs_bank_digest_recipient_ids = fields.Many2many(
        related='company_id.nhs_bank_digest_recipient_ids', readonly=False)
    nhs_bank_auto_create_portal_user = fields.Boolean(
        related='company_id.nhs_bank_auto_create_portal_user', readonly=False)
