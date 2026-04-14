# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FitnessAttendance(models.Model):
    _name = 'fitness.attendance'
    _description = 'Fitness Attendance'

    member_id = fields.Many2one('fitness.member', string='Member', required=True)
    check_in = fields.Datetime(string='Check In', default=fields.Datetime.now, required=True)
    check_out = fields.Datetime(string='Check Out')
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    method = fields.Selection([
        ('manual', 'Manual'),
        ('barcode', 'Barcode'),
        ('qr', 'QR Code'),
        ('portal', 'Portal'),
    ], string='Check-in Method', default='manual')
    check_in_user_id = fields.Many2one(
        'res.users',
        string='Checked In By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    check_out_user_id = fields.Many2one(
        'res.users',
        string='Checked Out By',
        readonly=True,
    )

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                diff = record.check_out - record.check_in
                record.duration = diff.total_seconds() / 3600.0
            else:
                record.duration = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_check_in_out_order(self):
        for record in self:
            if record.check_in and record.check_out and record.check_out < record.check_in:
                raise ValidationError("Check Out cannot be earlier than Check In.")

    @api.constrains('member_id', 'check_out')
    def _check_single_open_session(self):
        for record in self:
            if not record.member_id or record.check_out:
                continue
            if self.search_count([
                ('id', '!=', record.id),
                ('member_id', '=', record.member_id.id),
                ('check_out', '=', False),
            ]):
                raise ValidationError("This member already has an open attendance session.")

    def action_check_out_now(self):
        """Quick action to close an open attendance session."""
        now = fields.Datetime.now()
        for record in self:
            if record.check_out:
                continue
            record.write({
                'check_out': now,
                'check_out_user_id': self.env.user.id,
            })
        return True

    @api.model
    def _get_member_for_user(self, user_id):
        """Return the fitness.member linked to the given res.users id (via partner_id)."""
        if not user_id:
            return self.env['fitness.member']
        user = self.env['res.users'].sudo().browse(int(user_id))
        if not user.exists() or not user.partner_id:
            return self.env['fitness.member']
        return self.env['fitness.member'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)

    @api.model
    def portal_check_in_for_user(self, user_id):
        """Auto check-in on login. Safe no-op if already checked in or no member."""
        member = self._get_member_for_user(user_id)
        if not member:
            return False

        open_attendance = self.sudo().search([
            ('member_id', '=', member.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)
        if open_attendance:
            return open_attendance

        return self.sudo().create({
            'member_id': member.id,
            'check_in': fields.Datetime.now(),
            'method': 'portal',
            'check_in_user_id': int(user_id),
        })

    @api.model
    def portal_check_out_for_user(self, user_id):
        """Auto check-out on logout. Safe no-op if no open attendance or no member."""
        member = self._get_member_for_user(user_id)
        if not member:
            return False

        open_attendance = self.sudo().search([
            ('member_id', '=', member.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)
        if not open_attendance:
            return False

        open_attendance.write({
            'check_out': fields.Datetime.now(),
            'check_out_user_id': int(user_id),
        })
        return True
