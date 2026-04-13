# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class FitnessMember(models.Model):
    _name = 'fitness.member'
    _description = 'Fitness Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='cascade', help='Link to a partner')
    member_id = fields.Char(string='Member ID', required=True, copy=False, readonly=True, default='New')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', tracking=True)
    dob = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    phone = fields.Char(string='Phone', related='partner_id.phone', readonly=False, tracking=True)
    email = fields.Char(string='Email', related='partner_id.email', readonly=False, tracking=True)
    photo = fields.Binary(string='Photo')
    health_notes = fields.Text(string='Health Notes')
    membership_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('frozen', 'Frozen'),
        ('cancelled', 'Cancelled')
    ], string='Membership Status', default='active', tracking=True)
    join_date = fields.Date(string='Join Date', default=fields.Date.context_today)

    @api.depends('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = date.today()
                record.age = today.year - record.dob.year - ((today.month, today.day) < (record.dob.month, record.dob.day))
            else:
                record.age = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('member_id', 'New') == 'New':
                vals['member_id'] = self.env['ir.sequence'].next_by_code('fitness.member') or 'New'
        return super(FitnessMember, self).create(vals_list)

    @api.model
    def get_dashboard_data(self):
        """Return all dashboard KPIs and data for the OWL dashboard."""
        # KPIs
        total_members = self.search_count([])
        active_subs = self.env['fitness.subscription'].search_count([('state', '=', 'active')])
        total_trainers = self.env['fitness.trainer'].search_count([])
        total_classes = self.env['fitness.class'].search_count([])
        pending_bookings = self.env['fitness.class.booking'].search_count([('state', '=', 'draft')])
        active_equipment = self.env['fitness.equipment'].search_count([('status', '=', 'available')])
        maintenance_due = self.env['fitness.equipment.maintenance'].search_count([])

        # Revenue
        payments = self.env['fitness.payment'].search([])
        total_revenue = sum(payments.mapped('amount'))

        # Recent Members (last 5)
        recent = self.search([], order='create_date desc', limit=5)
        recent_members = [{
            'id': m.id,
            'name': m.name,
            'email': m.email or '-',
            'phone': m.phone or '-',
        } for m in recent]

        # Subscription Statistics
        all_subs = self.env['fitness.subscription'].search([])
        state_labels = dict(self.env['fitness.subscription']._fields['state'].selection)
        state_counts = {}
        for sub in all_subs:
            state_counts[sub.state] = state_counts.get(sub.state, 0) + 1
        total_subs = len(all_subs) or 1
        subscription_stats = [{
            'state': state,
            'label': state_labels.get(state, state),
            'count': count,
            'percentage': round((count / total_subs) * 100),
        } for state, count in state_counts.items()]

        # Plan Distribution
        plans = self.env['fitness.membership.plan'].search([])
        plan_distribution = []
        for plan in plans:
            cnt = self.env['fitness.subscription'].search_count([('plan_id', '=', plan.id)])
            plan_distribution.append({
                'name': plan.name,
                'count': cnt,
                'percentage': round((cnt / total_subs) * 100) if total_subs else 0,
            })

        # Recent Payments (last 5)
        recent_pays = self.env['fitness.payment'].search([], order='payment_date desc', limit=5)
        method_labels = dict(self.env['fitness.payment']._fields['payment_method'].selection)
        recent_payments = [{
            'id': p.id,
            'date': str(p.payment_date) if p.payment_date else '-',
            'member': p.subscription_id.member_id.name if p.subscription_id and p.subscription_id.member_id else '-',
            'amount': p.amount,
            'method': method_labels.get(p.payment_method, p.payment_method),
        } for p in recent_pays]

        return {
            'total_members': total_members,
            'active_subscriptions': active_subs,
            'total_revenue': round(total_revenue, 2),
            'total_trainers': total_trainers,
            'total_classes': total_classes,
            'pending_bookings': pending_bookings,
            'active_equipment': active_equipment,
            'maintenance_due': maintenance_due,
            'recent_members': recent_members,
            'subscription_stats': subscription_stats,
            'plan_distribution': plan_distribution,
            'recent_payments': recent_payments,
        }
