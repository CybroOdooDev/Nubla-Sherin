# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import date

class FitnessPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        # We only count these if they are present in counters
        if 'fitness_member_count' in counters:
            member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            values['fitness_member_count'] = 1 if member else 0
            
        if 'fitness_trainer_count' in counters:
            trainer = request.env['fitness.trainer'].sudo().search([('employee_id.user_id.partner_id', '=', partner.id)], limit=1)
            values['fitness_trainer_count'] = 1 if trainer else 0
            
        if 'fitness_manager_count' in counters:
            is_manager = request.env.user.has_group('fitness_center_management.group_fitness_manager')
            values['fitness_manager_count'] = 1 if is_manager else 0
            
        return values

    # ==========================
    # MEMBER PORTAL ROUTES
    # ==========================

    @http.route(['/my/fitness', '/my/fitness/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_fitness_dashboard(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.render("fitness_center_management.portal_fitness_not_member", values)
            
        subscription = request.env['fitness.subscription'].sudo().search([
            ('member_id', '=', member.id)
        ], order='start_date desc', limit=1)
        
        bookings = request.env['fitness.class.booking'].sudo().search([
            ('member_id', '=', member.id),
            ('state', 'in', ['booked', 'attended'])
        ], order='create_date desc', limit=5)
        
        values.update({
            'member': member,
            'subscription': subscription,
            'bookings': bookings,
            'page_name': 'fitness_dashboard',
        })
        return request.render("fitness_center_management.portal_my_fitness_dashboard", values)

    @http.route(['/my/fitness/subscription'], type='http', auth="user", website=True)
    def portal_my_fitness_subscription(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my/fitness')
            
        subscriptions = request.env['fitness.subscription'].sudo().search([
            ('member_id', '=', member.id)
        ], order='start_date desc')
        
        values.update({
            'member': member,
            'subscriptions': subscriptions,
            'page_name': 'fitness_subscription',
        })
        return request.render("fitness_center_management.portal_my_fitness_subscription", values)

    @http.route(['/my/fitness/bookings', '/my/fitness/bookings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_fitness_bookings(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my/fitness')
            
        # Pager logic
        domain = [('member_id', '=', member.id)]
        booking_count = request.env['fitness.class.booking'].sudo().search_count(domain)
        pager = portal_pager(
            url="/my/fitness/bookings",
            total=booking_count,
            page=page,
            step=10,
        )
        bookings = request.env['fitness.class.booking'].sudo().search(
            domain, order="create_date desc", limit=10, offset=pager['offset']
        )
        
        values.update({
            'member': member,
            'bookings': bookings,
            'pager': pager,
            'page_name': 'fitness_bookings',
            'default_url': '/my/fitness/bookings',
        })
        return request.render("fitness_center_management.portal_my_fitness_bookings", values)

    @http.route(['/my/fitness/checkins', '/my/fitness/checkins/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_fitness_checkins(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my/fitness')
            
        domain = [('member_id', '=', member.id)]
        checkin_count = request.env['fitness.attendance'].sudo().search_count(domain)
        pager = portal_pager(
            url="/my/fitness/checkins",
            total=checkin_count,
            page=page,
            step=10,
        )
        checkins = request.env['fitness.attendance'].sudo().search(
            domain, order="check_in desc", limit=10, offset=pager['offset']
        )
        
        values.update({
            'member': member,
            'checkins': checkins,
            'pager': pager,
            'page_name': 'fitness_checkins',
            'default_url': '/my/fitness/checkins',
        })
        return request.render("fitness_center_management.portal_my_fitness_checkins", values)

    @http.route(['/my/fitness/profile'], type='http', auth="user", website=True)
    def portal_my_fitness_profile(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my/fitness')
            
        values.update({
            'member': member,
            'page_name': 'fitness_profile',
        })
        return request.render("fitness_center_management.portal_my_fitness_profile", values)

    @http.route(['/my/fitness/invoices'], type='http', auth="user", website=True)
    def portal_my_fitness_invoices(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['fitness.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my/fitness')
            
        invoices = request.env['account.move'].sudo().search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice')
        ], order='invoice_date desc')
        
        values.update({
            'member': member,
            'invoices': invoices,
            'page_name': 'fitness_invoices',
        })
        return request.render("fitness_center_management.portal_my_fitness_invoices", values)

    # ==========================
    # TRAINER PORTAL ROUTES
    # ==========================
    
    @http.route(['/my/trainer'], type='http', auth="user", website=True)
    def portal_my_trainer_dashboard(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        trainer = request.env['fitness.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not trainer:
            return request.render("fitness_center_management.portal_trainer_not_trainer", values)
            
        classes = request.env['fitness.class.schedule'].sudo().search([
            ('trainer_id', '=', trainer.id),
            ('state', 'in', ['scheduled', 'in_progress'])
        ], order='date_start asc', limit=5)
        
        clients = request.env['fitness.member'].sudo().search([
            ('pt_plan_ids', '!=', False) # Simple client association logic for now
        ], limit=5)
        
        values.update({
            'trainer': trainer,
            'classes': classes,
            'clients': clients,
            'page_name': 'trainer_dashboard',
        })
        return request.render("fitness_center_management.portal_my_trainer_dashboard", values)
        
    @http.route(['/my/trainer/classes'], type='http', auth="user", website=True)
    def portal_my_trainer_classes(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        trainer = request.env['fitness.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not trainer:
            return request.redirect('/my/trainer')
            
        classes = request.env['fitness.class.schedule'].sudo().search([
            ('trainer_id', '=', trainer.id)
        ], order='date_start desc')
        
        values.update({
            'trainer': trainer,
            'classes': classes,
            'page_name': 'trainer_classes',
        })
        return request.render("fitness_center_management.portal_my_trainer_classes", values)

    @http.route(['/my/trainer/clients'], type='http', auth="user", website=True)
    def portal_my_trainer_clients(self, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        trainer = request.env['fitness.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not trainer:
            return request.redirect('/my/trainer')
            
        clients = request.env['fitness.member'].sudo().search([
            ('pt_plan_ids', '!=', False)
        ])
        
        values.update({
            'trainer': trainer,
            'clients': clients,
            'page_name': 'trainer_clients',
        })
        return request.render("fitness_center_management.portal_my_trainer_clients", values)

    # ==========================
    # MANAGER PORTAL ROUTES
    # ==========================

    @http.route(['/my/manager'], type='http', auth="user", website=True)
    def portal_my_manager_dashboard(self, **kw):
        values = self._prepare_portal_layout_values()
        is_manager = request.env.user.has_group('fitness_center_management.group_fitness_manager')
        
        if not is_manager:
            return request.redirect('/my/home')
            
        member_count = request.env['fitness.member'].sudo().search_count([])
        trainer_count = request.env['fitness.trainer'].sudo().search_count([])
        active_subscriptions = request.env['fitness.subscription'].sudo().search_count([('state', '=', 'active')])
        active_classes = request.env['fitness.class.schedule'].sudo().search_count([('state', '=', 'scheduled')])
        
        values.update({
            'member_count': member_count,
            'trainer_count': trainer_count,
            'active_subscriptions': active_subscriptions,
            'active_classes': active_classes,
            'page_name': 'manager_dashboard',
        })
        return request.render("fitness_center_management.portal_my_manager_dashboard", values)

    @http.route(['/my/manager/members'], type='http', auth="user", website=True)
    def portal_my_manager_members(self, **kw):
        if not request.env.user.has_group('fitness_center_management.group_fitness_manager'):
            return request.redirect('/my/home')
            
        values = self._prepare_portal_layout_values()
        members = request.env['fitness.member'].sudo().search([])
        
        values.update({
            'members': members,
            'page_name': 'manager_members',
        })
        return request.render("fitness_center_management.portal_my_manager_members", values)

    @http.route(['/my/manager/member/<model("fitness.member"):member>'], type='http', auth="user", website=True)
    def portal_my_manager_member_detail(self, member, **kw):
        if not request.env.user.has_group('fitness_center_management.group_fitness_manager'):
            return request.redirect('/my/home')
            
        values = self._prepare_portal_layout_values()
        subscriptions = request.env['fitness.subscription'].sudo().search([('member_id', '=', member.id)])
        bookings = request.env['fitness.class.booking'].sudo().search([('member_id', '=', member.id)])
        
        values.update({
            'target_member': member,
            'subscriptions': subscriptions,
            'bookings': bookings,
            'page_name': 'manager_member_detail',
        })
        return request.render("fitness_center_management.portal_my_manager_member_detail", values)

