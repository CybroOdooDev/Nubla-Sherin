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
#############################################################################
from collections import defaultdict

from odoo import http
from odoo.http import request

# Simple per-IP in-memory rate limiter (resets on server restart)
_rate_limit_store = defaultdict(int)
_RATE_LIMIT = 10  # max submissions per IP per session lifetime


class PublicComplaintController(http.Controller):

    @http.route('/complaint/submit/<string:token>', auth='public', website=True, csrf=True)
    def public_complaint_form(self, token, **kw):
        company = self._get_company_by_token(token)
        if not company:
            return request.not_found()

        error = kw.get('error')
        return request.render('odoo_nhs_complaints.public_complaint_form', {
            'token': token,
            'organisation_name': company.name,
            'error': error,
        })

    @http.route('/complaint/submit/<string:token>', auth='public', website=True,
                csrf=True, methods=['POST'])
    def public_complaint_submit(self, token, **post):
        company = self._get_company_by_token(token)
        if not company:
            return request.not_found()

        # Honeypot check (bot detection)
        if post.get('honeypot_check'):
            return request.render('odoo_nhs_complaints.public_complaint_confirm', {
                'reference': 'PALS/SUBMITTED',
            })

        # Per-IP rate limiting
        client_ip = request.httprequest.remote_addr or 'unknown'
        _rate_limit_store[client_ip] += 1
        if _rate_limit_store[client_ip] > _RATE_LIMIT:
            return request.render('odoo_nhs_complaints.public_complaint_form', {
                'token': token,
                'organisation_name': company.name,
                'error': 'Too many submissions from your IP address. Please try again later.',
            })

        record_type = post.get('record_type', 'pals')
        subject_summary = post.get('subject_summary', '').strip()
        description = post.get('description', '').strip()
        is_anonymous = bool(post.get('is_anonymous'))
        is_third_party = post.get('is_third_party') == '1'
        event_date = post.get('event_date') or False

        if not subject_summary or not description:
            return request.render('odoo_nhs_complaints.public_complaint_form', {
                'token': token,
                'organisation_name': company.name,
                'error': 'Please fill in all required fields.',
            })

        # Build complaint vals
        vals = {
            'record_type': record_type,
            'subject_summary': subject_summary,
            'description': description,
            'received_via': 'website',
            'company_id': company.id,
            'is_anonymous': is_anonymous,
            'is_third_party': is_third_party,
            'event_date': event_date or False,
            'consent_status': 'pending' if is_third_party else 'not_required',
        }

        # Build complainant if not anonymous
        if not is_anonymous:
            complainant_name = post.get('complainant_name', '').strip()
            complainant_email = post.get('complainant_email', '').strip()
            complainant_phone = post.get('complainant_phone', '').strip()
            if complainant_name:
                Complainant = request.env['nhs.complainant'].sudo()
                complainant = Complainant.create({
                    'name': complainant_name,
                    'email': complainant_email,
                    'phone': complainant_phone,
                    'relationship_to_patient': 'relative' if is_third_party else 'self',
                })
                vals['complainant_id'] = complainant.id

        # Find default subject (fallback)
        default_subject = request.env['nhs.complaint.subject'].sudo().search(
            [('parent_id', '=', False)], limit=1)
        if default_subject:
            vals['subject_id'] = default_subject.id
        else:
            return request.render('odoo_nhs_complaints.public_complaint_form', {
                'token': token,
                'organisation_name': company.name,
                'error': 'Complaint subjects are not configured. Please contact the Complaints Team directly.',
            })

        complaint = request.env['nhs.complaint'].sudo().create(vals)
        return request.render('odoo_nhs_complaints.public_complaint_confirm', {
            'reference': complaint.name,
        })

    def _get_company_by_token(self, token):
        IrParam = request.env['ir.config_parameter'].sudo()
        stored_token = IrParam.get_param('odoo_nhs_complaints.public_form_token', '')
        form_enabled = IrParam.get_param('odoo_nhs_complaints.public_form_enabled', 'False')
        if form_enabled not in ('True', '1', 'true') or stored_token != token:
            return None
        return request.env.company
