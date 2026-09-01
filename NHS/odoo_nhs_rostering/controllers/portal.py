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
from odoo import http, fields
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class NhsRosterPortal(CustomerPortal):
    """Staff self-service: view the published roster, request leave and see
    the balance, and propose/respond to duty swaps. Ownership is always
    resolved server-side from the logged-in user, never trusted from the
    request - the same pattern as the Staff Bank portal."""

    def _get_member(self):
        """ Method for get member """
        return request.env['nhs.workforce.member'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)

    def _prepare_home_portal_values(self, counters):
        """ Method for prepare home portal values """
        values = super()._prepare_home_portal_values(counters)
        member = self._get_member()
        if member:
            values['roster_duty_count'] = request.env['nhs.duty.assignment'].sudo().search_count([
                ('member_id', '=', member.id), ('state', '=', 'published'),
                ('duty_date', '>=', fields.Date.context_today(member)),
            ])
        else:
            values['roster_duty_count'] = None
        return values

    @http.route(['/my/roster'], type='http', auth='user', website=True)
    def portal_roster_home(self, **kw):
        """ Method for portal roster home """
        member = self._get_member()
        if not member:
            return request.render('odoo_nhs_rostering.portal_roster_not_member', {})
        today = fields.Date.context_today(member)
        upcoming = request.env['nhs.duty.assignment'].sudo().search([
            ('member_id', '=', member.id), ('state', '=', 'published'), ('duty_date', '>=', today),
        ], order='duty_date', limit=10)
        pending_swaps = request.env['nhs.swap.request'].sudo().search([
            '|', ('requester_member_id', '=', member.id), ('target_member_id', '=', member.id),
            ('state', 'in', ('proposed', 'accepted_by_target')),
        ])
        values = {
            'member': member, 'upcoming_duties': upcoming, 'pending_swaps': pending_swaps,
            'page_name': 'roster_home',
        }
        return request.render('odoo_nhs_rostering.portal_roster_home', values)

    @http.route(['/my/roster/duties'], type='http', auth='user', website=True)
    def portal_roster_duties(self, **kw):
        """ Method for portal roster duties """
        member = self._get_member()
        if not member:
            return request.redirect('/my/roster')
        duties = request.env['nhs.duty.assignment'].sudo().search([
            ('member_id', '=', member.id), ('state', 'in', ('published', 'worked', 'dna')),
        ], order='duty_date desc')
        values = {'member': member, 'duties': duties, 'page_name': 'roster_duties'}
        return request.render('odoo_nhs_rostering.portal_roster_duties', values)

    @http.route(['/my/roster/leave'], type='http', auth='user', website=True)
    def portal_roster_leave(self, **kw):
        """ Method for portal roster leave """
        member = self._get_member()
        if not member:
            return request.redirect('/my/roster')
        requests_ = request.env['nhs.leave.request'].sudo().search(
            [('member_id', '=', member.id)], order='date_from desc')
        entitlements = request.env['nhs.leave.entitlement'].sudo().search(
            [('member_id', '=', member.id)])
        leave_types = request.env['nhs.leave.type'].sudo().search([('active', '=', True)])
        values = {
            'member': member, 'leave_requests': requests_, 'entitlements': entitlements,
            'leave_types': leave_types, 'page_name': 'roster_leave', 'error': kw.get('error'),
        }
        return request.render('odoo_nhs_rostering.portal_roster_leave', values)

    @http.route(['/my/roster/leave/request'], type='http', auth='user', website=True, methods=['POST'])
    def portal_roster_leave_request(self, **kw):
        """ Method for portal roster leave request """
        member = self._get_member()
        if member:
            try:
                leave = request.env['nhs.leave.request'].sudo().create({
                    'member_id': member.id,
                    'leave_type_id': int(kw.get('leave_type_id')) if kw.get('leave_type_id') else False,
                    'date_from': kw.get('date_from'),
                    'date_to': kw.get('date_to'),
                    'reason': kw.get('reason'),
                })
                leave.action_submit()
            except (ValidationError, UserError) as exc:
                return request.redirect('/my/roster/leave?error=%s' % str(exc))
        return request.redirect('/my/roster/leave')

    @http.route(['/my/roster/leave/<int:leave_id>/cancel'], type='http', auth='user', website=True, methods=['POST'])
    def portal_roster_leave_cancel(self, leave_id, **kw):
        """ Method for portal roster leave cancel """
        member = self._get_member()
        leave = request.env['nhs.leave.request'].sudo().browse(leave_id).exists()
        if member and leave and leave.member_id == member:
            leave.action_cancel()
        return request.redirect('/my/roster/leave')

    @http.route(['/my/roster/swaps'], type='http', auth='user', website=True)
    def portal_roster_swaps(self, **kw):
        """ Method for portal roster swaps """
        member = self._get_member()
        if not member:
            return request.redirect('/my/roster')
        swaps = request.env['nhs.swap.request'].sudo().search([
            '|', ('requester_member_id', '=', member.id), ('target_member_id', '=', member.id),
        ], order='create_date desc')
        own_duties = request.env['nhs.duty.assignment'].sudo().search([
            ('member_id', '=', member.id), ('state', '=', 'published'),
        ], order='duty_date')
        values = {
            'member': member, 'swaps': swaps, 'own_duties': own_duties,
            'page_name': 'roster_swaps', 'error': kw.get('error'),
        }
        return request.render('odoo_nhs_rostering.portal_roster_swaps', values)

    @http.route(['/my/roster/swaps/propose'], type='http', auth='user', website=True, methods=['POST'])
    def portal_roster_swap_propose(self, **kw):
        """ Method for portal roster swap propose """
        member = self._get_member()
        if member:
            try:
                own_assignment = request.env['nhs.duty.assignment'].sudo().browse(
                    int(kw.get('requester_assignment_id'))).exists()
                target_assignment = request.env['nhs.duty.assignment'].sudo().browse(
                    int(kw.get('target_assignment_id'))).exists()
                if not own_assignment or own_assignment.member_id != member:
                    raise UserError('Choose one of your own published duties to offer.')
                swap = request.env['nhs.swap.request'].sudo().create({
                    'requester_assignment_id': own_assignment.id,
                    'target_assignment_id': target_assignment.id,
                    'notes': kw.get('notes'),
                })
                swap.action_propose()
            except (ValidationError, UserError) as exc:
                return request.redirect('/my/roster/swaps?error=%s' % str(exc))
        return request.redirect('/my/roster/swaps')

    @http.route(['/my/roster/swaps/<int:swap_id>/accept'], type='http', auth='user', website=True, methods=['POST'])
    def portal_roster_swap_accept(self, swap_id, **kw):
        """ Method for portal roster swap accept """
        member = self._get_member()
        swap = request.env['nhs.swap.request'].sudo().browse(swap_id).exists()
        if member and swap and swap.target_member_id == member:
            try:
                swap.action_accept_by_target()
            except (ValidationError, UserError) as exc:
                return request.redirect('/my/roster/swaps?error=%s' % str(exc))
        return request.redirect('/my/roster/swaps')

    @http.route(['/my/roster/swaps/<int:swap_id>/reject'], type='http', auth='user', website=True, methods=['POST'])
    def portal_roster_swap_reject(self, swap_id, **kw):
        """ Method for portal roster swap reject """
        member = self._get_member()
        swap = request.env['nhs.swap.request'].sudo().browse(swap_id).exists()
        if member and swap and member in (swap.requester_member_id, swap.target_member_id):
            swap.action_reject()
        return request.redirect('/my/roster/swaps')

