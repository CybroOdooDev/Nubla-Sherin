# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from datetime import date

class FitnessHome(Home):
    def _login_redirect(self, uid, redirect=None):
        user = request.env['res.users'].sudo().browse(uid)
        
        # Override default /web or the old /fitness/dashboard redirect with our portal routes
        if not redirect or redirect == '/web' or redirect == '/fitness/dashboard':
            if user.has_group('fitness_center_management.group_fitness_manager'):
                return '/my/manager'
            elif request.env['fitness.trainer'].sudo().search_count([('employee_id.user_id.partner_id', '=', user.partner_id.id)]):
                return '/my/trainer'
            elif request.env['fitness.member'].sudo().search_count([('partner_id', '=', user.partner_id.id)]):
                # Auto attendance check-in for members when logging into the Fitness website area.
                request.env['fitness.attendance'].sudo().portal_check_in_for_user(uid)
                return '/my/fitness'
                
        return super(FitnessHome, self)._login_redirect(uid, redirect=redirect)

class FitnessWebsite(http.Controller):

    @http.route(['/fitness'], type='http', auth="public", website=True)
    def fitness_index(self, **post):
        trainers = request.env['fitness.trainer'].sudo().search([], limit=4)
        classes = request.env['fitness.class'].sudo().search([], limit=3)
        return request.render("fitness_center_management.fitness_index", {
            'trainers': trainers,
            'classes': classes,
        })

    @http.route(['/fitness/membership'], type='http', auth="public", website=True)
    def fitness_membership(self, **post):
        plans = request.env['fitness.membership.plan'].sudo().search([('active', '=', True)])
        return request.render("fitness_center_management.fitness_membership_plans", {
            'plans': plans,
        })

    @http.route(['/fitness/classes'], type='http', auth="public", website=True)
    def fitness_classes(self, **post):
        schedules = request.env['fitness.class.schedule'].sudo().search([('state', '=', 'scheduled')], order='date_start asc')
        return request.render("fitness_center_management.fitness_classes_schedule", {
            'schedules': schedules,
        })

    @http.route(['/fitness/classes/book'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def fitness_class_book(self, **post):
        schedule_id = post.get('schedule_id')
        if not schedule_id:
            return request.redirect('/fitness/classes')

        schedule = request.env['fitness.class.schedule'].sudo().browse(int(schedule_id))
        if not schedule.exists():
            return request.redirect('/fitness/classes')

        # Find member linked to current user
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1,
        )
        if not member:
            return request.redirect('/fitness/classes?error=no_member')

        # Check if already booked
        Booking = request.env['fitness.class.booking'].sudo()
        existing = Booking.search([
            ('schedule_id', '=', schedule.id),
            ('member_id', '=', member.id),
            ('state', '!=', 'cancelled'),
        ], limit=1)
        if existing:
            return request.redirect('/fitness/classes?error=already_booked')

        # Check availability
        if schedule.available_spots <= 0:
            return request.redirect('/fitness/classes?error=full')

        # Create booking
        Booking.create({
            'schedule_id': schedule.id,
            'member_id': member.id,
        })
        return request.redirect('/fitness/classes?success=1')

    @http.route(['/fitness/trainers'], type='http', auth="public", website=True)
    def fitness_trainers(self, **post):
        trainers = request.env['fitness.trainer'].sudo().search([])
        return request.render("fitness_center_management.fitness_trainers", {
            'trainers': trainers,
        })

    @http.route(['/fitness/join/<model("fitness.membership.plan"):plan>'], type='http', auth="public", website=True)
    def fitness_join_form(self, plan, **post):
        return request.render("fitness_center_management.fitness_join_form", {
            'plan': plan,
        })

    @http.route(['/fitness/join/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def fitness_join_submit(self, **post):
        plan_id = post.get('plan_id')
        name = post.get('name')
        email = post.get('email')
        phone = post.get('phone')
        
        if not all([plan_id, name, email]):
            return request.redirect('/fitness/membership')
            
        # Create or find partner, preferring the logged-in user if not public
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
        else:
            partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                })
            
        # Check if fitness member exists
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not member:
            member = request.env['fitness.member'].sudo().create({
                'name': name,
                'partner_id': partner.id,
                'email': email,
                'phone': phone,
            })
            
        # Create subscription
        subscription = request.env['fitness.subscription'].sudo().create({
            'member_id': member.id,
            'plan_id': int(plan_id),
            'state': 'draft',
        })
        
        # Determine income account for invoice line safely
        plan = request.env['fitness.membership.plan'].sudo().browse(int(plan_id))
        journal = request.env['account.journal'].sudo().search([('type', '=', 'sale')], limit=1)
        
        account_id = False
        if journal and getattr(journal, 'default_account_id', False):
            account_id = journal.default_account_id.id
        if not account_id:
            account = request.env['account.account'].sudo().search([('account_type', '=', 'income_other')], limit=1)
            if not account:
                account = request.env['account.account'].sudo().search([('internal_group', '=', 'income')], limit=1)
            account_id = account.id if account else False

        line_vals = {
            'name': f"Fitness Plan: {plan.name}",
            'quantity': 1,
            'price_unit': plan.price,
        }
        if account_id:
            line_vals['account_id'] = account_id

        # Create Invoice
        invoice = request.env['account.move'].sudo().create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        })
        
        try:
            invoice.sudo().action_post()
        except Exception as e:
            # If posting fails due to configuration, leave it as draft, portal will still display it
            pass
            
        subscription.sudo().write({'invoice_ids': [(4, invoice.id)]})
        
        # Redirect directly to portal payment page
        return request.redirect(invoice.get_portal_url())

    @http.route(['/fitness/router'], type='http', auth="user", website=True)
    def fitness_portal_router(self, **post):
        user = request.env.user
        
        if user.has_group('fitness_center_management.group_fitness_manager'):
            return request.redirect('/my/manager')
            
        is_trainer = request.env['fitness.trainer'].sudo().search_count([('employee_id.user_id.partner_id', '=', user.partner_id.id)])
        if is_trainer:
            return request.redirect('/my/trainer')
            
        return request.redirect('/my/fitness')

