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
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# IP rate-limit: max 10 submissions per window
_RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds
_RATE_LIMIT_MAX = 10
_ip_submissions: dict = defaultdict(list)


def _check_rate_limit(ip):
    """Return False and reject if ip has already made _RATE_LIMIT_MAX submissions
    within the current _RATE_LIMIT_WINDOW; otherwise record this submission and
    return True. State is kept in-memory per process, not persisted."""
    now = datetime.now()
    window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW)
    _ip_submissions[ip] = [t for t in _ip_submissions[ip] if t > window_start]
    if len(_ip_submissions[ip]) >= _RATE_LIMIT_MAX:
        return False
    _ip_submissions[ip].append(now)
    return True


class NhsRecruitmentPublic(http.Controller):
    """Public-facing controller serving the anonymous/token-based recruitment
    application portal, reusing the suite's proven token-gated form pattern."""

    def _company_from_token(self, token):
        """Look up the company whose public-form token matches, returning
        None if there's no match or the public application form is
        disabled."""
        Company = request.env['res.company'].sudo()
        company = Company.search([('nhs_recruit_public_form_token', '=', token)], limit=1)
        if not company or not company.nhs_recruit_public_form_enabled:
            return None
        return company

    @http.route('/jobs/apply/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def vacancy_list(self, token, **kw):
        """List currently open vacancies for the company matching token,
        excluding internal-only vacancies for anyone who isn't logged in
        as an internal user (matches the gate on the apply route itself)."""
        company = self._company_from_token(token)
        if not company:
            return request.not_found()

        domain = [
            ('company_id', '=', company.id),
            ('state', 'in', ('open', 'in_progress')),
            ('internal_only', '=', False),
        ]
        vacancies = request.env['nhs.vacancy'].sudo().search(domain)
        return request.render('odoo_nhs_recruitment.public_vacancy_list', {
            'token': token,
            'company': company,
            'vacancies': vacancies,
        })

    @http.route('/jobs/apply/<string:token>/<int:vacancy_id>', type='http', auth='public',
                website=False, sitemap=False)
    def application_form(self, token, vacancy_id, **kw):
        """Render the public application form for one open vacancy."""
        company = self._company_from_token(token)
        if not company:
            return request.not_found()

        vacancy = request.env['nhs.vacancy'].sudo().browse(vacancy_id)
        if not vacancy.exists() or vacancy.company_id.id != company.id \
                or vacancy.state not in ('open', 'in_progress') \
                or vacancy.internal_only:
            return request.not_found()

        return request.render('odoo_nhs_recruitment.public_application_form', {
            'token': token,
            'company': company,
            'vacancy': vacancy,
        })

    @http.route('/jobs/apply/<string:token>/<int:vacancy_id>/submit', type='http', auth='public',
                methods=['POST'], csrf=True)
    def application_submit(self, token, vacancy_id, **post):
        """Validate, rate-limit, honeypot-check, then create the candidate,
        application and segregated equality-monitoring record as sudo."""
        company = self._company_from_token(token)
        if not company:
            return request.not_found()

        vacancy = request.env['nhs.vacancy'].sudo().browse(vacancy_id)
        if not vacancy.exists() or vacancy.company_id.id != company.id or vacancy.internal_only:
            return request.not_found()

        ip = request.httprequest.remote_addr
        if not _check_rate_limit(ip):
            return request.render('odoo_nhs_recruitment.public_application_thank_you',
                                   {'reference': 'RATE_LIMITED'})

        # Honeypot: hidden field bots fill in, humans don't
        if post.get('website_url'):
            return request.not_found()

        name = post.get('name', '').strip()
        email = post.get('email', '').strip()
        if not name or not email:
            return request.render('odoo_nhs_recruitment.public_application_form', {
                'token': token, 'company': company, 'vacancy': vacancy,
                'error': 'Please fill in all required fields.',
            })

        Candidate = request.env['nhs.candidate'].sudo()
        candidate = Candidate.search([
            ('email', '=', email), ('company_id', '=', company.id)], limit=1)
        if not candidate:
            candidate = Candidate.create({
                'name': name,
                'email': email,
                'phone': post.get('phone', ''),
                'company_id': company.id,
            })

        application = request.env['nhs.application'].sudo().create({
            'vacancy_id': vacancy.id,
            'candidate_id': candidate.id,
            'source': 'portal',
            'supporting_statement': post.get('supporting_statement', ''),
            'employment_history': post.get('employment_history', ''),
            'right_to_work_flagged': bool(post.get('right_to_work_flagged')),
            'registration_flagged': bool(post.get('registration_flagged')),
        })

        if application.equality_id:
            application.equality_id.sudo().write({
                'age_band': post.get('age_band') or False,
                'ethnicity': post.get('ethnicity') or False,
                'disability': post.get('disability') or False,
                'sex': post.get('sex') or False,
                'religion': post.get('religion', ''),
                'sexual_orientation': post.get('sexual_orientation', ''),
            })

        application.action_send_acknowledgement()

        return request.render('odoo_nhs_recruitment.public_application_thank_you', {
            'reference': application.name,
        })
