import logging
from collections import defaultdict
from datetime import datetime, timedelta

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

# IP rate-limit: max 10 submissions per window
_RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds
_RATE_LIMIT_MAX = 10
_ip_submissions: dict = defaultdict(list)


def _check_rate_limit(ip):
    now = datetime.now()
    window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW)
    _ip_submissions[ip] = [t for t in _ip_submissions[ip] if t > window_start]
    if len(_ip_submissions[ip]) >= _RATE_LIMIT_MAX:
        return False
    _ip_submissions[ip].append(now)
    return True


class NhsPublicReport(http.Controller):

    def _company_from_token(self, token):
        Company = request.env['res.company'].sudo()
        company = Company.search([('public_form_token', '=', token)], limit=1)
        if not company or not company.public_form_enabled:
            return None
        return company

    @http.route('/incident/report/<string:token>',
                type='http', auth='public', website=False, sitemap=False)
    def report_form(self, token, **kw):
        company = self._company_from_token(token)
        if not company:
            return request.not_found()

        Terminology = request.env['nhs.terminology'].sudo()
        provider_type = company.provider_type or 'nhs_trust'

        person_label = Terminology.t('person_affected', provider_type)
        provider_name = company.name

        # Build category list (only active, leaf-level for this provider)
        categories = request.env['nhs.incident.category'].sudo().search([
            ('active', '=', True),
        ])
        cat_list = []
        for c in categories:
            types = c.provider_types or ''
            if not types or provider_type in types.split(','):
                cat_list.append({'id': c.id, 'complete_name': c.complete_name})

        # Build location list
        locations = request.env['nhs.location'].sudo().search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ])
        loc_list = [{'id': l.id, 'complete_name': l.complete_name} for l in locations]

        values = {
            'token': token,
            'company': company,
            'provider_name': provider_name,
            'person_label': person_label,
            'categories': cat_list,
            'locations': loc_list,
            'anonymous_allowed': company.anonymous_reporting_allowed,
        }
        return request.render(
            'odoo_nhs_incident_risk.public_report_form', values)

    @http.route('/incident/report/<string:token>/submit',
                type='http', auth='public', methods=['POST'], csrf=True)
    def report_submit(self, token, **post):
        company = self._company_from_token(token)
        if not company:
            return request.not_found()

        # Rate limiting
        ip = request.httprequest.remote_addr
        if not _check_rate_limit(ip):
            return request.render(
                'odoo_nhs_incident_risk.public_report_thank_you',
                {'reference': 'RATE_LIMITED', 'email_sent': False})

        # Honeypot check (hidden field; bots fill it, humans don't)
        if post.get('website_url'):
            return request.not_found()

        # Parse form values
        is_anonymous = bool(post.get('is_anonymous'))
        occurred_at_str = post.get('occurred_at', '').replace('T', ' ')
        try:
            occurred_at = datetime.strptime(occurred_at_str, '%Y-%m-%d %H:%M')
        except ValueError:
            occurred_at = fields.Datetime.now()

        vals = {
            'company_id': company.id,
            'incident_kind': post.get('incident_kind', 'incident'),
            'occurred_at': occurred_at,
            'reported_at': fields.Datetime.now(),
            'location_id': int(post.get('location_id') or 0) or False,
            'category_id': int(post.get('category_id') or 0) or False,
            'description': post.get('description', ''),
            'immediate_action': post.get('immediate_action', ''),
            'is_anonymous': is_anonymous,
            'reporter_name': '' if is_anonymous else post.get('reporter_name', ''),
            'reporter_email': '' if is_anonymous else post.get('reporter_email', ''),
            'reporter_role': post.get('reporter_role', ''),
            'reported_via': 'public_form',
        }

        # Validate required fields
        if not vals['location_id'] or not vals['category_id'] or not vals['description']:
            return request.render(
                'odoo_nhs_incident_risk.public_report_form',
                {'error': 'Please fill in all required fields.',
                 'token': token, 'company': company})

        incident = request.env['nhs.incident'].sudo().create(vals)

        # Parse persons
        idx = 0
        while f'person_type_{idx}' in post:
            ptype = post.get(f'person_type_{idx}')
            pname = post.get(f'person_name_{idx}', '')
            pharm = post.get(f'person_harm_{idx}', 'none')
            if ptype:
                request.env['nhs.incident.person'].sudo().create({
                    'incident_id': incident.id,
                    'person_type': ptype,
                    'name': pname,
                    'harm_observed': pharm,
                    'sequence': idx * 10,
                })
            idx += 1

        # Send acknowledgement email
        email_sent = False
        if not is_anonymous and vals['reporter_email']:
            template = request.env.ref(
                'odoo_nhs_incident_risk.mail_template_reporter_ack',
                raise_if_not_found=False)
            if template:
                try:
                    template.sudo().send_mail(incident.id, force_send=True)
                    email_sent = True
                except Exception:
                    _logger.warning('Failed to send acknowledgement email for %s', incident.name)

        return request.render(
            'odoo_nhs_incident_risk.public_report_thank_you',
            {'reference': incident.name, 'email_sent': email_sent})
