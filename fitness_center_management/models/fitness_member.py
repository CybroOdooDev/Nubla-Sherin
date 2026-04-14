# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class FitnessMember(models.Model):
    _name = 'fitness.member'
    _description = 'Fitness Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Profile & Identity ──────────────────────────────────────────────
    name = fields.Char(string='Name', required=True, tracking=True)
    image_1920 = fields.Binary(string='Photo')
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner',
        ondelete='cascade', help='Link to a partner',
    )
    member_id = fields.Char(
        string='Member ID', required=True, copy=False,
        readonly=True, default='New',
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', tracking=True)
    dob = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('o+', 'O+'), ('o-', 'O-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
    ], string='Blood Group')
    nationality = fields.Many2one('res.country', string='Nationality')
    id_number = fields.Char(string='ID / Passport Number')

    # ── Contact ─────────────────────────────────────────────────────────
    phone = fields.Char(
        string='Phone', related='partner_id.phone',
        readonly=False, tracking=True,
    )
    email = fields.Char(
        string='Email', related='partner_id.email',
        readonly=False, tracking=True,
    )
    photo = fields.Binary(string='Legacy Photo')
    membership_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('frozen', 'Frozen'),
        ('cancelled', 'Cancelled'),
    ], string='Membership Status', default='active', tracking=True)
    join_date = fields.Date(
        string='Join Date', default=fields.Date.context_today,
    )

    # ── Address ─────────────────────────────────────────────────────────
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # ── Physical Metrics ────────────────────────────────────────────────
    height = fields.Float(string='Height (cm)')
    weight = fields.Float(string='Weight (kg)')
    bmi = fields.Float(
        string='BMI', compute='_compute_bmi',
        store=True, digits=(4, 1),
    )

    # ── Emergency Contact ───────────────────────────────────────────────
    emergency_contact_name = fields.Char(string='Contact Name')
    emergency_contact_phone = fields.Char(string='Contact Phone')
    emergency_contact_relation = fields.Char(string='Relation')

    # ── Fitness Goals & Preferences ─────────────────────────────────────
    fitness_goal = fields.Selection([
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('endurance', 'Endurance'),
        ('flexibility', 'Flexibility'),
        ('general', 'General Fitness'),
    ], string='Fitness Goal')
    preferred_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    ], string='Preferred Time')
    trainer_id = fields.Many2one('fitness.trainer', string='Personal Trainer')
    notes = fields.Text(string='Notes')

    # ── Medical ─────────────────────────────────────────────────────────
    health_notes = fields.Text(string='Health Notes')
    medical_conditions = fields.Text(string='Medical Conditions')
    allergies = fields.Text(string='Allergies')
    doctor_name = fields.Char(string='Doctor Name')
    doctor_phone = fields.Char(string='Doctor Phone')

    # ── Attendance ──────────────────────────────────────────────────────
    attendance_ids = fields.One2many(
        'fitness.attendance', 'member_id', string='Attendance Logs',
    )
    attendance_count = fields.Integer(
        string='Attendances', compute='_compute_attendance_stats',
    )
    open_attendance_id = fields.Many2one(
        'fitness.attendance', string='Open Attendance',
        compute='_compute_attendance_stats',
    )
    is_checked_in = fields.Boolean(
        string='Checked In', compute='_compute_attendance_stats',
    )

    # ── Subscriptions ───────────────────────────────────────────────────
    subscription_ids = fields.One2many(
        'fitness.subscription', 'member_id', string='Subscriptions',
    )
    subscription_count = fields.Integer(
        string='Subscriptions', compute='_compute_subscription_count',
    )

    # ── Bookings ────────────────────────────────────────────────────────
    booking_ids = fields.One2many(
        'fitness.class.booking', 'member_id', string='Class Bookings',
    )
    booking_count = fields.Integer(
        string='Bookings', compute='_compute_booking_count',
    )

    # ── Payments (via subscriptions) ────────────────────────────────────
    payment_count = fields.Integer(
        string='Payments', compute='_compute_payment_count',
    )

    @api.depends('attendance_ids')
    def _compute_attendance_stats(self):
        Attendance = self.env['fitness.attendance']
        if not self.ids:
            for member in self:
                member.attendance_count = 0
                member.open_attendance_id = False
                member.is_checked_in = False
            return

        counts = Attendance.read_group(
            [('member_id', 'in', self.ids)],
            ['member_id'],
            ['member_id'],
        )
        count_map = {c['member_id'][0]: c['member_id_count'] for c in counts if c.get('member_id')}

        open_att = Attendance.search(
            [('member_id', 'in', self.ids), ('check_out', '=', False)],
            order='check_in desc',
        )
        open_map = {}
        for att in open_att:
            mid = att.member_id.id
            if mid not in open_map:
                open_map[mid] = att

        for member in self:
            member.attendance_count = count_map.get(member.id, 0)
            member.open_attendance_id = open_map.get(member.id)
            member.is_checked_in = bool(open_map.get(member.id))

    @api.depends('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = date.today()
                record.age = today.year - record.dob.year - ((today.month, today.day) < (record.dob.month, record.dob.day))
            else:
                record.age = 0

    @api.depends('height', 'weight')
    def _compute_bmi(self):
        for record in self:
            if record.height and record.weight and record.height > 0:
                height_m = record.height / 100.0
                record.bmi = round(record.weight / (height_m ** 2), 1)
            else:
                record.bmi = 0.0

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for member in self:
            member.subscription_count = len(member.subscription_ids)

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for member in self:
            member.booking_count = len(member.booking_ids)

    def _compute_payment_count(self):
        Payment = self.env['fitness.payment']
        for member in self:
            member.payment_count = Payment.search_count([
                ('subscription_id.member_id', '=', member.id),
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('member_id', 'New') == 'New':
                vals['member_id'] = self.env['ir.sequence'].next_by_code('fitness.member') or 'New'
        return super(FitnessMember, self).create(vals_list)

    def action_check_in(self):
        Attendance = self.env['fitness.attendance']
        now = fields.Datetime.now()
        for member in self:
            if member.membership_status != 'active':
                raise UserError("Only active members can be checked in.")
            if Attendance.search_count([('member_id', '=', member.id), ('check_out', '=', False)]):
                raise UserError("This member is already checked in.")
            Attendance.create({
                'member_id': member.id,
                'check_in': now,
                'method': 'manual',
                'check_in_user_id': self.env.user.id,
            })
        return True

    def action_check_out(self):
        Attendance = self.env['fitness.attendance']
        now = fields.Datetime.now()
        for member in self:
            open_att = Attendance.search(
                [('member_id', '=', member.id), ('check_out', '=', False)],
                order='check_in desc',
                limit=1,
            )
            if not open_att:
                raise UserError("No open attendance session found for this member.")
            open_att.write({
                'check_out': now,
                'check_out_user_id': self.env.user.id,
            })
        return True

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'res_model': 'fitness.attendance',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'res_model': 'fitness.subscription',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Class Bookings',
            'res_model': 'fitness.class.booking',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'fitness.payment',
            'view_mode': 'list,form',
            'domain': [('subscription_id.member_id', '=', self.id)],
        }

    @api.model
    def get_dashboard_data(self):
        """Return all dashboard KPIs and data for the OWL dashboard."""
        # KPIs
        total_members = self.sudo().search_count([])
        active_subs = self.env['fitness.subscription'].sudo().search_count([('state', '=', 'active')])
        total_trainers = self.env['fitness.trainer'].sudo().search_count([])
        total_classes = self.env['fitness.class'].sudo().search_count([])
        pending_bookings = self.env['fitness.class.booking'].sudo().search_count([('state', '=', 'draft')])
        active_equipment = self.env['fitness.equipment'].sudo().search_count([('status', '=', 'available')])
        maintenance_due = self.env['fitness.equipment.maintenance'].sudo().search_count([])

        # Revenue
        payments = self.env['fitness.payment'].sudo().search([])
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
        all_subs = self.env['fitness.subscription'].sudo().search([])
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
        recent_pays = self.env['fitness.payment'].sudo().search([], order='payment_date desc', limit=5)
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

    @api.model
    def _cron_send_notifications(self):
        """Cron job to send notifications for membership renewals and class schedules."""
        # 1. Membership renewals (e.g. expiring in 3 days)
        three_days_from_now = fields.Date.context_today(self) + fields.date_utils.relativedelta(days=3)
        expiring_subs = self.env['fitness.subscription'].search([
            ('end_date', '=', three_days_from_now),
            ('state', '=', 'active')
        ])
        for sub in expiring_subs:
            sub.member_id.message_post(
                body=f"Reminder: Your subscription '{sub.plan_id.name}' expires on {sub.end_date}. Please renew soon!",
                subject="Membership Renewal Reminder"
            )

        # 2. Upcoming Training Sessions
        today = fields.Date.context_today(self)
        sessions_today = self.env['fitness.training.session'].search([
            ('start_time', '>=', today),
            ('start_time', '<=', today + fields.date_utils.relativedelta(days=1)),
            ('state', 'in', ['scheduled', 'draft'])
        ])
        for session in sessions_today:
            for member in session.member_ids:
                member.message_post(
                    body=f"Reminder: You have a training session '{session.name}' scheduled today at {session.start_time}.",
                    subject="Upcoming Training Session"
                )
