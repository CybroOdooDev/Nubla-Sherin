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
from datetime import datetime
import pytz
from odoo import http, fields
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class NhsStaffBankPortal(CustomerPortal):
    """Bank-member self-service: see available shifts, express interest /
    accept, view bookings and pay summary, set availability. Reuses the
    suite's proven portal pattern (auth='user', ownership enforced
    server-side rather than trusted from the request)."""

    def _get_bank_member(self):
        """The nhs.bank.member linked to the logged-in portal user, if any."""
        return request.env['nhs.bank.member'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)

    @staticmethod
    def _parse_portal_datetime(value):
        """Parse an HTML <input type="datetime-local"> value (e.g.
        '2026-08-17T10:44'), interpreted in the logged-in user's timezone,
        into a naive UTC datetime suitable for storing in a Datetime field.
        Returns False if the value is missing or malformed."""
        if not value:
            return False
        try:
            naive = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        except ValueError:
            return False
        try:
            local_tz = pytz.timezone(request.env.user.tz or 'UTC')
        except pytz.UnknownTimeZoneError:
            local_tz = pytz.UTC
        return local_tz.localize(naive).astimezone(pytz.UTC).replace(tzinfo=None)

    @staticmethod
    def _local_now_str():
        """Current time in the logged-in user's timezone, formatted for use
        as the 'min' attribute of a <input type="datetime-local">, so the
        date picker itself won't offer a past date/time."""
        try:
            local_tz = pytz.timezone(request.env.user.tz or 'UTC')
        except pytz.UnknownTimeZoneError:
            local_tz = pytz.UTC
        now_local = pytz.UTC.localize(fields.Datetime.now()).astimezone(local_tz)
        return now_local.strftime('%Y-%m-%dT%H:%M')

    def _prepare_home_portal_values(self, counters):
        """Add the bank shift counter (eligible open shifts) to the portal
        home page's values, when the logged-in user is a bank member."""
        values = super()._prepare_home_portal_values(counters)
        member = self._get_bank_member()
        if member:
            gate = request.env['nhs.compliance.gate'].sudo()
            open_shifts = request.env['nhs.bank.shift'].sudo().search(
                [('state', 'in', ('open', 'partially_filled'))])
            values['bank_shift_count'] = len(
                open_shifts.filtered(lambda s: gate.eligibility(s, member)['eligible']))
        else:
            values['bank_shift_count'] = None
        return values

    @http.route(['/my/bank'], type='http', auth='user', website=True)
    def portal_bank_home(self, **kw):
        """`/my/bank`: the bank member's landing page, with a preview of
        eligible open shifts and upcoming bookings; renders the not-a-member
        page for users with no linked bank member."""
        member = self._get_bank_member()
        if not member:
            return request.render('odoo_nhs_staff_bank.portal_bank_not_member', {})
        open_shifts = request.env['nhs.bank.shift'].sudo().search(
            [('state', 'in', ('open', 'partially_filled'))])
        gate = request.env['nhs.compliance.gate'].sudo()
        eligible_shifts = open_shifts.filtered(lambda s: gate.eligibility(s, member)['eligible'])
        bookings = member.booking_ids.filtered(lambda b: b.state in ('booked', 'worked'))
        values = {
            'member': member,
            'eligible_shifts': eligible_shifts[:5],
            'upcoming_bookings': bookings.sorted('shift_start')[:5],
            'page_name': 'bank_home',
        }
        return request.render('odoo_nhs_staff_bank.portal_bank_home', values)

    @http.route(['/my/bank/shifts'], type='http', auth='user', website=True)
    def portal_bank_shifts(self, **kw):
        """`/my/bank/shifts`: lists all open shifts the member is eligible
        for, so they can express interest / accept."""
        member = self._get_bank_member()
        if not member:
            return request.redirect('/my/bank')
        open_shifts = request.env['nhs.bank.shift'].sudo().search(
            [('state', 'in', ('open', 'partially_filled'))], order='shift_start')
        gate = request.env['nhs.compliance.gate'].sudo()
        eligible_shifts = open_shifts.filtered(lambda s: gate.eligibility(s, member)['eligible'])
        values = {
            'member': member,
            'shifts': eligible_shifts,
            'page_name': 'bank_shifts',
        }
        return request.render('odoo_nhs_staff_bank.portal_bank_shifts', values)

    @http.route(['/my/bank/shifts/<int:shift_id>/accept'], type='http', auth='user', website=True, methods=['POST'])
    def portal_bank_shift_accept(self, shift_id, **kw):
        """`/my/bank/shifts/<id>/accept`: creates (or reuses) a pending offer
        for the member on this shift and accepts it, provided the member is
        still eligible; then redirects back to the shift list."""
        member = self._get_bank_member()
        shift = request.env['nhs.bank.shift'].sudo().browse(shift_id).exists()
        if member and shift:
            gate = request.env['nhs.compliance.gate'].sudo()
            outcome = gate.eligibility(shift, member)
            if outcome['eligible']:
                offer = shift.offer_ids.filtered(
                    lambda o: o.member_id == member and o.response == 'pending')
                if not offer:
                    offer = request.env['nhs.shift.offer'].sudo().create({
                        'shift_id': shift.id, 'member_id': member.id,
                    })
                try:
                    offer.sudo().action_accept()
                except Exception:
                    pass
        return request.redirect('/my/bank/shifts')

    @http.route(['/my/bank/offers/<int:offer_id>/decline'], type='http', auth='user', website=True, methods=['POST'])
    def portal_bank_offer_decline(self, offer_id, **kw):
        """`/my/bank/offers/<id>/decline`: declines the member's own pending
        offer (with an optional reason) and redirects back to the shift
        list."""
        member = self._get_bank_member()
        offer = request.env['nhs.shift.offer'].sudo().browse(offer_id).exists()
        if member and offer and offer.member_id == member:
            offer.sudo().action_decline(reason=kw.get('reason'))
        return request.redirect('/my/bank/shifts')

    @http.route(['/my/bank/bookings'], type='http', auth='user', website=True)
    def portal_bank_bookings(self, **kw):
        """`/my/bank/bookings`: lists the member's own bookings, newest first,
        with total pay for worked shifts."""
        member = self._get_bank_member()
        if not member:
            return request.redirect('/my/bank')
        bookings = member.booking_ids.sorted('shift_start', reverse=True)
        total_pay = sum(bookings.filtered(lambda b: b.state == 'worked').mapped('payable_amount'))
        values = {
            'member': member,
            'bookings': bookings,
            'total_pay': total_pay,
            'page_name': 'bank_bookings',
        }
        return request.render('odoo_nhs_staff_bank.portal_bank_bookings', values)

    @http.route(['/my/bank/availability'], type='http', auth='user', website=True)
    def portal_bank_availability(self, **kw):
        """`/my/bank/availability`: lists the member's own availability and
        blackout records, newest first."""
        member = self._get_bank_member()
        if not member:
            return request.redirect('/my/bank')
        values = {
            'member': member,
            'availability': member.availability_ids.sorted('date_from', reverse=True),
            'page_name': 'bank_availability',
            'min_datetime': self._local_now_str(),
        }
        return request.render('odoo_nhs_staff_bank.portal_bank_availability', values)

    @http.route(['/my/bank/availability/add'], type='http', auth='user', website=True, methods=['POST'])
    def portal_bank_availability_add(self, **kw):
        """`/my/bank/availability/add`: creates a new availability/blackout
        record for the member from submitted form data, then redirects back
        to the availability page. On a validation error (e.g. a past date,
        or 'To' before 'From'), re-renders the page with the error shown
        instead of crashing or silently dropping the submission."""
        member = self._get_bank_member()
        date_from = self._parse_portal_datetime(kw.get('date_from'))
        date_to = self._parse_portal_datetime(kw.get('date_to'))
        error = None
        if member and date_from and date_to:
            try:
                request.env['nhs.member.availability'].sudo().create({
                    'member_id': member.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'availability_type': kw.get('availability_type') or 'available',
                    'note': kw.get('note'),
                })
            except (ValidationError, UserError) as exc:
                error = str(exc)
        if error:
            values = {
                'member': member,
                'availability': member.availability_ids.sorted('date_from', reverse=True),
                'page_name': 'bank_availability',
                'min_datetime': self._local_now_str(),
                'error': error,
            }
            return request.render('odoo_nhs_staff_bank.portal_bank_availability', values)
        return request.redirect('/my/bank/availability')
