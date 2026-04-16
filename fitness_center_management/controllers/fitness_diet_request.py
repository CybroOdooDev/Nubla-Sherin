# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FitnessDietRequest(http.Controller):

    @http.route('/diet-request', type='http', auth='public', website=True)
    def diet_request_form(self, **kwargs):
        categories = request.env['fitness.diet.category'].sudo().search([])
        diet_types = request.env['fitness.diet.type'].sudo().search([])
        return request.render('fitness_center_management.diet_request_page', {
            'categories': categories,
            'diet_types': diet_types,
        })

    @http.route('/diet-request/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def diet_request_submit(self, **post):
        vals = {
            'name': post.get('title', 'Diet Request'),
            'contact_name': post.get('name'),
            'email_from': post.get('email'),
            'phone': post.get('phone'),
            'type': 'lead',
            'description': post.get('description'),
        }
        # Optional fields
        if post.get('birthdate'):
            vals['birthdate'] = post.get('birthdate')
        if post.get('gender'):
            vals['gender'] = post.get('gender')
        if post.get('diet_category_id'):
            vals['diet_category_id'] = int(post.get('diet_category_id'))
        if post.get('diet_type_id'):
            vals['diet_type_id'] = int(post.get('diet_type_id'))
        if post.get('description'):
            vals['diet_description'] = post.get('description')

        request.env['crm.lead'].sudo().create(vals)
        return request.render('fitness_center_management.diet_request_thanks')
