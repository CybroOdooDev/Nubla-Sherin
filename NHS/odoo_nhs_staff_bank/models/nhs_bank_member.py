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
from odoo import _, api, fields, models

MEMBER_TYPES = [
    ('substantive_bank', 'Substantive Staff Doing Bank'),
    ('bank_only', 'Bank-Only Worker'),
]

STATES = [
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('suspended', 'Suspended'),
]

COMPLIANCE_STATUSES = [
    ('compliant', 'Compliant'),
    ('non_compliant', 'Non-Compliant'),
    ('unknown', 'Unknown'),
]


class NhsBankMember(models.Model):
    """A flexible/bank worker: either a substantive member of staff picking up
    extra bank shifts, or a dedicated bank-only worker with no substantive
    post. Holds the roles/bands/skills/areas that drive shift eligibility,
    and a compliance status resolved through the compliance gate."""
    _name = 'nhs.bank.member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A flexible/bank worker'
    _order = 'name'

    name = fields.Char(
        string='Member Name',
        required=True,
        tracking=True,
        help="Bank member name."
    )
    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Bank member reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company."
    )
    member_type = fields.Selection(
        MEMBER_TYPES,
        string='Member Type',
        required=True,
        default='bank_only',
        tracking=True,
        help="Substantive staff doing extra bank shifts, or a dedicated bank-only"
             " worker with no substantive post."
    )
    workforce_member_id = fields.Reference(
        selection=[('nhs.workforce.member', 'Workforce Member')],
        string='Workforce Member (Training)',
        help="Optional soft link to the Mandatory Training module's workforce-member"
             " record — the source of real compliance data when that module is"
             " installed. A Reference field, not a Many2one, so this module never"
             " requires odoo_nhs_training to be installed."
    )
    post_id = fields.Many2one(
        'nhs.establishment.post',
        string='Substantive Post',
        help="The substantive post this member also holds, for substantive-doing-bank"
             " members (informational; used for working-time awareness)."
    )
    user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        help="Linked user for portal self-service (accept shifts, set availability,"
             " see own pay)."
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help="Contact record for email/phone."
    )
    email = fields.Char(
        string='Email',
        help="Email address used for offer/booking notifications."
    )
    phone = fields.Char(
        string='Phone',
    )
    role_ids = fields.Many2many(
        'nhs.staff.group',
        'nhs_bank_member_staff_group_rel',
        'member_id', 'staff_group_id',
        string='Roles',
        help="Roles/staff groups the member can work (from the Establishment"
             " Register's standard NHS staff-group reference)."
    )
    band_id = fields.Many2one(
        'nhs.afc.band',
        string='Primary Band',
        tracking=True,
        help="Primary Agenda for Change band."
    )
    skill_ids = fields.Many2many(
        'nhs.skill',
        'nhs_bank_member_skill_rel',
        'member_id', 'skill_id',
        string='Skills / Competencies',
        help="Competencies held — drives shift eligibility."
    )
    area_ids = fields.Many2many(
        'nhs.org.unit',
        'nhs_bank_member_org_unit_rel',
        'member_id', 'org_unit_id',
        string='Cleared Areas',
        help="Areas/wards the member is cleared to work in."
    )
    checks_confirmed = fields.Boolean(
        string='Employment Checks Confirmed',
        tracking=True,
        help="Employment checks (NHS Employment Check Standards) confirmed."
             " Only checked workers should be made active."
    )
    manual_compliance_flag = fields.Boolean(
        string='Manually Marked Compliant',
        default=True,
        help="Standalone fallback used only when the Mandatory Training module is"
             " not installed, so the compliance gate still functions: tick off"
             " when this member's training/registration is confirmed current."
    )
    manual_compliance_note = fields.Char(
        string='Compliance Note',
        help="Free-text reason shown when the manual compliance flag is off"
             " (fallback mode only)."
    )
    compliance_status = fields.Selection(
        COMPLIANCE_STATUSES,
        string='Compliance Status',
        compute='_compute_compliance_status',
        store=True,
        help="compliant / non_compliant / unknown, resolved by the compliance gate"
             " (training + registration, or the fallback flag)."
    )
    compliance_reason = fields.Char(
        string='Compliance Reason',
        compute='_compute_compliance_status',
        store=True,
        help="Reason surfaced when the member is non-compliant."
    )
    state = fields.Selection(
        STATES,
        string='Status',
        required=True,
        default='active',
        tracking=True,
        help="Active / inactive / suspended (e.g. pending re-check)."
    )
    join_date = fields.Date(
        string='Bank Join Date',
        default=fields.Date.context_today,
        help="Date the member joined the bank."
    )
    preferred_shift_type_ids = fields.Many2many(
        'nhs.shift.type',
        'nhs_bank_member_shift_type_rel',
        'member_id', 'shift_type_id',
        string='Preferred Shift Types',
        help="Preferred shift types / working preferences."
    )
    weekly_hours_limit = fields.Float(
        string='Weekly Hours Limit Override',
        help="Override of the company's default safe/legal weekly hours limit for"
             " this member. Leave blank to use the company default."
    )
    substantive_weekly_hours = fields.Float(
        string='Substantive Weekly Hours',
        help="Contracted hours in the member's substantive post, if any — added to"
             " booked bank hours for the working-time awareness check."
    )
    availability_ids = fields.One2many(
        'nhs.member.availability',
        'member_id',
        string='Availability',
        help="Availability/blackout records."
    )
    availability_count = fields.Integer(
        string='Availability Count',
        compute='_compute_availability_count',
    )
    offer_ids = fields.One2many(
        'nhs.shift.offer',
        'member_id',
        string='Offers',
        help="Shift offers made to this member."
    )
    offer_count = fields.Integer(
        string='Offer Count',
        compute='_compute_offer_count',
    )
    booking_ids = fields.One2many(
        'nhs.shift.booking',
        'member_id',
        string='Bookings',
        help="Their bookings."
    )
    booking_count = fields.Integer(
        string='Booking Count',
        compute='_compute_booking_count',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag. Leavers are archived, retaining their history."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Assign a sequence reference when not provided."""
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.bank.member') or 'New'
        return super().create(vals_list)

    @api.depends('workforce_member_id', 'checks_confirmed', 'manual_compliance_flag',
                 'manual_compliance_note', 'state')
    def _compute_compliance_status(self):
        """Resolve compliance status/reason through the compliance gate."""
        gate = self.env['nhs.compliance.gate']
        for member in self:
            if member.state != 'active':
                member.compliance_status = 'unknown'
                member.compliance_reason = _("Member is not active.")
                continue
            compliant, reason = gate.is_member_compliant_with_reason(member)
            member.compliance_status = 'compliant' if compliant else 'non_compliant'
            member.compliance_reason = reason

    def _compute_availability_count(self):
        for member in self:
            member.availability_count = len(member.availability_ids)

    def _compute_offer_count(self):
        for member in self:
            member.offer_count = len(member.offer_ids)

    def _compute_booking_count(self):
        for member in self:
            member.booking_count = len(member.booking_ids)

    def _is_available_for(self, shift_start, shift_end):
        """True if this member has declared availability spanning the whole
        of [shift_start, shift_end] and no overlapping blackout."""
        self.ensure_one()
        blackout = self.availability_ids.filtered(
            lambda a: a.availability_type == 'unavailable'
            and a.date_from < shift_end and a.date_to > shift_start)
        if blackout:
            return False
        available = self.availability_ids.filtered(
            lambda a: a.availability_type == 'available'
            and a.date_from <= shift_start and a.date_to >= shift_end)
        return bool(available)

    def get_booked_hours(self, date_from, date_to):
        """Sum of booked/worked hours for this member within [date_from, date_to]."""
        self.ensure_one()
        bookings = self.booking_ids.filtered(
            lambda b: b.state in ('booked', 'worked')
            and b.shift_start < date_to and b.shift_end > date_from)
        total = 0.0
        for booking in bookings:
            delta = booking.shift_end - booking.shift_start
            total += delta.total_seconds() / 3600.0
        return total

    def check_working_time_breach(self, additional_hours, date_from, date_to):
        """True if adding `additional_hours` in [date_from, date_to] would push
        this member over their safe/legal weekly hours limit (substantive +
        bank), per the Working Time Regulations."""
        self.ensure_one()
        limit = self.weekly_hours_limit or self.env.company.nhs_bank_weekly_hours_limit
        if not limit:
            return False
        projected = self.substantive_weekly_hours + self.get_booked_hours(date_from, date_to) + additional_hours
        return projected > limit

    def action_view_availability(self):
        self.ensure_one()
        return {
            'name': _('Availability'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.member.availability',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_offers(self):
        self.ensure_one()
        return {
            'name': _('Offers'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.shift.offer',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
        }

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'name': _('Bookings'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.shift.booking',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
        }

    @api.model
    def _cron_recompute_compliance(self):
        """Scheduled action: refresh every active member's compliance status
        and alert the bank coordinators about anyone who has newly become
        non-compliant, so they are not offered/booked while lapsed."""
        members = self.search([('state', '=', 'active')])
        before = {m.id: m.compliance_status for m in members}
        members._compute_compliance_status()
        template = self.env.ref('odoo_nhs_staff_bank.mail_template_compliance_alert', raise_if_not_found=False)
        if not template:
            return
        for member in members:
            if before.get(member.id) != 'non_compliant' and member.compliance_status == 'non_compliant':
                template.send_mail(member.id, force_send=True)
