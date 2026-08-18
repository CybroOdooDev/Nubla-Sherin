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
from odoo.exceptions import UserError, ValidationError

REASONS = [
    ('sickness', 'Sickness Cover'),
    ('vacancy', 'Vacancy Cover'),
    ('demand', 'Extra Demand'),
    ('special', 'Special'),
]

URGENCY = [
    ('planned', 'Planned'),
    ('urgent', 'Urgent'),
    ('last_minute', 'Last-Minute'),
]

STATES = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('partially_filled', 'Partially Filled'),
    ('filled', 'Filled'),
    ('cancelled', 'Cancelled'),
    ('to_agency', 'To Agency'),
    ('agency_filled', 'Agency Filled'),
    ('expired', 'Expired'),
]

SOURCES = [
    ('manual', 'Manual'),
    ('roster', 'Rostering'),
]


class NhsBankShift(models.Model):
    """An open shift needing cover, offered to the bank. The spine of the
    module: gap identified -> open shift -> offer -> booking -> worked, or
    unfilled -> escalated to agency (the displacement metric)."""
    _name = 'nhs.bank.shift'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A shift needing cover, offered to the bank'
    _order = 'shift_start desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. 'Ward 7 — Night RN — 12 May'."
    )
    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Shift reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Area / Ward',
        required=True,
        tracking=True,
        help="Area/ward needing cover (Establishment org unit)."
    )
    shift_start = fields.Datetime(
        string='Start',
        required=True,
        tracking=True,
        help="Shift start date/time."
    )
    shift_end = fields.Datetime(
        string='End',
        required=True,
        tracking=True,
        help="Shift end date/time."
    )
    shift_type_id = fields.Many2one(
        'nhs.shift.type',
        string='Shift Type',
        help="Day / night / weekend / bank holiday — drives the rate applied."
    )
    band_id = fields.Many2one(
        'nhs.afc.band',
        string='Band',
        help="Required Agenda for Change band."
    )
    role = fields.Char(
        string='Role',
        help="Required role, e.g. 'Registered Nurse', 'HCA' (free text; matched"
             " loosely against a member's roles when computing eligibility)."
    )
    skill_ids = fields.Many2many(
        'nhs.skill',
        'nhs_bank_shift_skill_rel',
        'shift_id', 'skill_id',
        string='Skills Required',
        help="Skills required — filters eligible members."
    )
    headcount = fields.Integer(
        string='Headcount Needed',
        default=1,
        help="Number of workers needed for this shift."
    )
    reason = fields.Selection(
        REASONS,
        string='Reason',
        help="Sickness cover / vacancy cover / extra demand / special."
    )
    urgency = fields.Selection(
        URGENCY,
        string='Urgency',
        default='planned',
        tracking=True,
        help="Last-minute vs planned."
    )
    state = fields.Selection(
        STATES,
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help="draft / open / partially_filled / filled / cancelled / to_agency /"
             " expired. New shifts start as draft and are not offered to the bank"
             " or visible to bank members until opened."
    )
    source = fields.Selection(
        SOURCES,
        string='Source',
        default='manual',
        help="Created manually, or pushed in from the Rostering module (capstone)."
    )
    offer_cutoff = fields.Datetime(
        string='Offer Cutoff',
        help="Deadline by which the shift must be filled by the bank before it is"
             " considered for agency escalation."
    )
    time_range = fields.Char(
        string='Time',
        compute='_compute_time_range',
        help="Shift start-end time in the user's timezone, for compact display"
             " (e.g. on the kanban board)."
    )
    offer_ids = fields.One2many(
        'nhs.shift.offer',
        'shift_id',
        string='Offers',
        help="Offers made for this shift."
    )
    offer_count = fields.Integer(
        string='Offer Count',
        compute='_compute_offer_count',
    )
    booking_ids = fields.One2many(
        'nhs.shift.booking',
        'shift_id',
        string='Bookings',
        help="Bookings made for this shift."
    )
    filled_count = fields.Integer(
        string='Filled Count',
        compute='_compute_filled_count',
        store=True,
        help="Confirmed (non-cancelled) bookings vs headcount."
    )
    booking_count = fields.Integer(
        string='Booking Count',
        compute='_compute_booking_count',
        help="All bookings made for this shift, regardless of status —"
             " unlike Filled, which only counts confirmed (booked/worked) ones."
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help="Currency for cost fields."
    )
    estimated_cost = fields.Monetary(
        string='Estimated Bank Cost',
        compute='_compute_estimated_cost',
        store=True,
        currency_field='currency_id',
        help="Indicative bank cost from the rate card (headcount x hours x rate)."
    )
    rate_found = fields.Boolean(
        string='Rate Found',
        compute='_compute_estimated_cost',
        store=True,
        help="Whether a rate card matching this shift's band/shift type/date/"
             " company was found. If false, the estimated cost is not a genuine"
             " zero-cost shift — no applicable rate card is configured, so the"
             " cost cannot be estimated."
    )
    agency_cost = fields.Monetary(
        string='Agency Cost',
        currency_field='currency_id',
        help="Cost captured when this shift was escalated to agency — the comparator"
             " for the bank-vs-agency displacement metric."
    )
    agency_name = fields.Char(
        string='Agency',
        help="Agency the shift was escalated to."
    )
    agency_escalated_by_id = fields.Many2one(
        'res.users',
        string='Escalated By',
    )
    agency_escalated_at = fields.Datetime(
        string='Escalated At',
    )
    agency_escalation_reason = fields.Char(
        string='Escalation Reason',
    )
    agency_confirmed = fields.Boolean(
        string='Agency Confirmed',
        help="Ticked once the agency has actually completed/confirmed this shift."
             " Locks the escalation in — the shift can no longer be reopened once"
             " confirmed, only cancelled."
    )
    agency_confirmed_by_id = fields.Many2one(
        'res.users',
        string='Confirmed By',
    )
    agency_confirmed_at = fields.Datetime(
        string='Confirmed At',
    )
    cancel_reason = fields.Char(
        string='Cancel Reason',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.depends('org_unit_id', 'shift_type_id', 'shift_start', 'role')
    def _compute_name(self):
        """Build the display name from area, shift type/role and date."""
        for shift in self:
            date_part = fields.Datetime.context_timestamp(
                shift, shift.shift_start).strftime('%d %b') if shift.shift_start else ''
            middle = ' — '.join(filter(None, [
                shift.shift_type_id.name, shift.role or shift.band_id.name]))
            shift.name = ' — '.join(filter(None, [shift.org_unit_id.name, middle, date_part]))

    @api.depends('shift_start', 'shift_end')
    def _compute_time_range(self):
        """Compact 'HH:MM - HH:MM' display of the shift's start/end time."""
        for shift in self:
            if shift.shift_start and shift.shift_end:
                start = fields.Datetime.context_timestamp(shift, shift.shift_start)
                end = fields.Datetime.context_timestamp(shift, shift.shift_end)
                shift.time_range = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
            else:
                shift.time_range = False

    def _compute_offer_count(self):
        """Count of offers made for this shift."""
        for shift in self:
            shift.offer_count = len(shift.offer_ids)

    def _compute_booking_count(self):
        """Count of all bookings made for this shift, regardless of status."""
        for shift in self:
            shift.booking_count = len(shift.booking_ids)

    @api.depends('booking_ids.state', 'headcount')
    def _compute_filled_count(self):
        """Confirmed bookings (booked/worked) vs headcount drives the state machine."""
        for shift in self:
            confirmed = shift.booking_ids.filtered(lambda b: b.state in ('booked', 'worked'))
            shift.filled_count = len(confirmed)
            if shift.state not in ('draft', 'cancelled', 'to_agency', 'agency_filled', 'expired'):
                if shift.filled_count <= 0:
                    shift.state = 'open'
                elif shift.filled_count < shift.headcount:
                    shift.state = 'partially_filled'
                else:
                    shift.state = 'filled'

    @api.depends('band_id', 'role', 'shift_type_id', 'shift_start', 'shift_end',
                 'headcount', 'company_id')
    def _compute_estimated_cost(self):
        """Indicative bank cost = headcount x hours x best-matching rate."""
        Rate = self.env['nhs.bank.rate']
        for shift in self:
            if not (shift.shift_start and shift.shift_end):
                shift.estimated_cost = 0.0
                shift.rate_found = False
                continue
            hours = (shift.shift_end - shift.shift_start).total_seconds() / 3600.0
            rate = Rate._find_rate(
                band_id=shift.band_id.id, role=shift.role,
                shift_type_id=shift.shift_type_id.id,
                date=fields.Date.to_date(shift.shift_start),
                company_id=shift.company_id.id,
            )
            shift.rate_found = bool(rate)
            if rate:
                shift.estimated_cost = rate.compute_payable(hours) * max(shift.headcount, 1)
            else:
                shift.estimated_cost = 0.0

    @api.constrains('shift_start', 'shift_end')
    def _check_times(self):
        """Reject a shift whose end time is not after its start time, or whose
        start time is set in the past."""
        now = fields.Datetime.now()
        for shift in self:
            if shift.shift_end <= shift.shift_start:
                raise ValidationError("The shift end time must be after the start time.")
            if shift.shift_start < now:
                raise ValidationError("The shift start time cannot be in the past.")

    @api.constrains('headcount')
    def _check_headcount(self):
        """Reject a shift with a headcount below 1."""
        for shift in self:
            if shift.headcount < 1:
                raise ValidationError("Headcount must be at least 1.")

    @api.model_create_multi
    def create(self, vals_list):
        """Assign a sequence reference when not provided, and mark shifts
        already past their end time as expired."""
        now = fields.Datetime.now()
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.bank.shift') or 'New'
            if vals.get('shift_end'):
                end_dt = fields.Datetime.to_datetime(vals['shift_end'])
                if end_dt and end_dt < now:
                    vals['state'] = 'expired'
        return super().create(vals_list)

    def get_eligible_members(self):
        """All active bank members, annotated with eligibility (role/band +
        skills + area + available + compliant) for this shift. Returns a list
        of dicts: {'member': record, 'eligible': bool, 'reasons': [...]}."""
        self.ensure_one()
        gate = self.env['nhs.compliance.gate']
        members = self.env['nhs.bank.member'].search([('state', '=', 'active')])
        result = []
        for member in members:
            outcome = gate.eligibility(self, member)
            result.append({'member': member, 'eligible': outcome['eligible'], 'reasons': outcome['reasons']})
        return result

    def action_offer(self):
        """Open the offer wizard, pre-populated with eligible members."""
        self.ensure_one()
        return {
            'name': ('Offer Shift'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.offer.shift.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shift_id': self.id},
        }

    def action_escalate_agency(self):
        """Open the agency-escalation wizard to record the cost and reason."""
        self.ensure_one()
        return {
            'name': ('Escalate to Agency'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.escalate.agency.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shift_id': self.id},
        }

    def action_confirm_agency_filled(self):
        """Confirm that the agency has actually completed this shift: moves
        it to its own terminal 'Agency Filled' state, distinct from 'To
        Agency' (escalated, outcome still pending). Once here, the shift can
        no longer be reopened back into the bank pipeline — cancel it instead
        if the confirmation itself was wrong."""
        for shift in self:
            if shift.state != 'to_agency':
                raise UserError(("Only a shift that is escalated to agency can be"
                                  " confirmed as agency-filled."))
            shift.write({
                'state': 'agency_filled',
                'agency_confirmed': True,
                'agency_confirmed_by_id': self.env.user.id,
                'agency_confirmed_at': fields.Datetime.now(),
            })
            shift.message_post(body=("Agency booking confirmed as completed."))

    def action_open(self):
        """Confirm a draft shift, opening it for offering to the bank and
        making it visible to bank members/coordinators."""
        for shift in self:
            if shift.filled_count <= 0:
                shift.state = 'open'
            elif shift.filled_count < shift.headcount:
                shift.state = 'partially_filled'
            else:
                shift.state = 'filled'

    def action_cancel(self):
        """Cancel the shift, withdrawing any pending offers."""
        for shift in self:
            shift.offer_ids.filtered(lambda o: o.response == 'pending').write({'response': 'withdrawn'})
            shift.state = 'cancelled'

    def action_reset_open(self):
        """Manually reopen a cancelled/expired/to-agency shift. A confirmed
        'Agency Filled' shift cannot be reopened — that's a settled fact, not
        a mistake to undo; cancel the shift instead if the confirmation
        itself was wrong."""
        if any(shift.state == 'agency_filled' for shift in self):
            raise UserError(("Cannot reopen: the agency booking has already been"
                              " confirmed as completed."))
        self.write({'state': 'open'})

    def action_view_offers(self):
        """Open the offers made for this shift."""
        self.ensure_one()
        return {
            'name': ('Offers'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.shift.offer',
            'view_mode': 'list,form',
            'domain': [('shift_id', '=', self.id)],
            'context': {'default_shift_id': self.id},
        }

    def action_view_bookings(self):
        """Open the bookings made for this shift."""
        self.ensure_one()
        return {
            'name': ('Bookings'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.shift.booking',
            'view_mode': 'list,form',
            'domain': [('shift_id', '=', self.id)],
            'context': {'default_shift_id': self.id},
        }

    @api.model
    def _cron_send_coordinator_digest(self):
        """Scheduled action: daily digest of open/urgent shifts to the bank
        coordinator recipients configured in Settings."""
        recipients = self.env.company.nhs_bank_digest_recipients
        if not recipients:
            return
        open_shifts = self.search([('state', 'in', ('open', 'partially_filled'))])
        if not open_shifts:
            return
        urgent = open_shifts.filtered(lambda s: s.urgency in ('urgent', 'last_minute'))
        lines = ''.join(
            '<li>%s (%s)</li>' % (s.name, dict(URGENCY).get(s.urgency))
            for s in open_shifts[:30]
        )
        body = (
            "<p>Staff Bank daily digest: %(open)d open shift(s), %(urgent)d urgent/last-minute.</p>"
            "<ul>%(lines)s</ul>"
        ) % {'open': len(open_shifts), 'urgent': len(urgent), 'lines': lines}
        self.env['mail.mail'].sudo().create({
            'subject': 'Staff Bank Daily Digest — %d open shift(s)' % len(open_shifts),
            'body_html': body,
            'email_to': recipients,
        }).send()

    @api.model
    def _cron_expire_stale_shifts(self):
        """Scheduled action: shifts still draft/open/partially-filled well past
        their end time without being filled or escalated are marked expired
        (a draft never opened in time is stale too, not just a published one)."""
        stale = self.search([
            ('state', 'in', ('draft', 'open', 'partially_filled')),
            ('shift_end', '<', fields.Datetime.now()),
        ])
        stale.write({'state': 'expired'})

    @api.model
    def get_bank_dashboard_data(self):
        """Aggregated metrics for the client-side Fill-Rate / Bank-vs-Agency
        dashboard."""
        Shift = self.env['nhs.bank.shift']
        Booking = self.env['nhs.shift.booking']
        Member = self.env['nhs.bank.member']

        all_shifts = Shift.search([])
        resolved = all_shifts.filtered(lambda s: s.state in ('filled', 'to_agency', 'agency_filled', 'expired'))
        filled = resolved.filtered(lambda s: s.state == 'filled')
        fill_rate = (len(filled) / len(resolved) * 100.0) if resolved else 0.0

        open_shifts = all_shifts.filtered(lambda s: s.state in ('open', 'partially_filled'))
        urgent_unfilled = open_shifts.filtered(lambda s: s.urgency in ('urgent', 'last_minute'))

        bank_bookings = Booking.search([('state', 'in', ('booked', 'worked')), ('fill_source', '=', 'bank')])
        bank_spend = sum(bank_bookings.mapped('payable_amount'))
        agency_shifts = all_shifts.filtered(lambda s: s.state in ('to_agency', 'agency_filled'))
        agency_spend = sum(agency_shifts.mapped('agency_cost'))
        agency_comparator_pct = self.env.company.nhs_bank_agency_comparator_pct or 0.0
        cost_avoidance = bank_spend * (agency_comparator_pct / 100.0)

        utilisation = []
        for member in Member.search([('state', '=', 'active')], limit=500):
            worked = member.booking_ids.filtered(lambda b: b.state == 'worked')
            if worked:
                utilisation.append({
                    'id': member.id, 'name': member.name, 'shifts': len(worked),
                })
        utilisation.sort(key=lambda u: u['shifts'], reverse=True)

        compliance_exposure = Member.search([
            ('state', '=', 'active'), ('compliance_status', '=', 'non_compliant')])

        hotspots = {}
        for shift in open_shifts:
            hotspots.setdefault(shift.org_unit_id.id, {
                'id': shift.org_unit_id.id, 'name': shift.org_unit_id.display_name, 'count': 0})
            hotspots[shift.org_unit_id.id]['count'] += 1
        hotspot_list = sorted(hotspots.values(), key=lambda h: h['count'], reverse=True)[:8]

        return {
            'fill_rate': round(fill_rate, 1),
            'open_count': len(open_shifts),
            'urgent_unfilled_count': len(urgent_unfilled),
            'filled_count': len(filled),
            'to_agency_count': len(agency_shifts),
            'bank_spend': bank_spend,
            'agency_spend': agency_spend,
            'cost_avoidance': cost_avoidance,
            'compliance_exposure_count': len(compliance_exposure),
            'utilisation_top': utilisation[:10],
            'hotspots': hotspot_list,
            'open_list': [{
                'id': s.id, 'name': s.name, 'org_unit': s.org_unit_id.display_name,
                'state_label': dict(STATES).get(s.state), 'urgency': s.urgency,
            } for s in open_shifts[:15]],
            'compliance_list': [{
                'id': m.id, 'name': m.name, 'reason': m.compliance_reason,
            } for m in compliance_exposure[:15]],
        }
