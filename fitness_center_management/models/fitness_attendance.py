# -*- coding: utf-8 -*-
from odoo import models, fields, api

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
        ('qr', 'QR Code')
    ], string='Check-in Method', default='manual')

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                diff = record.check_out - record.check_in
                record.duration = diff.total_seconds() / 3600.0
            else:
                record.duration = 0.0
