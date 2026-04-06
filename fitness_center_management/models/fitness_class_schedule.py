# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessClassSchedule(models.Model):
    _name = 'fitness.class.schedule'
    _description = 'Fitness Class Schedule'

    class_id = fields.Many2one('fitness.class', string='Class', required=True)
    trainer_id = fields.Many2one('fitness.trainer', string='Trainer', required=True)
    date_start = fields.Datetime(string='Start Time', required=True)
    date_end = fields.Datetime(string='End Time', required=True)
    room = fields.Char(string='Room/Studio')
    current_bookings = fields.Integer(string='Current Bookings', compute='_compute_bookings', store=True)
    available_spots = fields.Integer(string='Available Spots', compute='_compute_available_spots', store=True)
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled')

    @api.depends('class_id')
    def _compute_bookings(self):
        for record in self:
            record.current_bookings = self.env['fitness.class.booking'].search_count([('schedule_id', '=', record.id)])

    @api.depends('class_id.max_capacity', 'current_bookings')
    def _compute_available_spots(self):
        for record in self:
            record.available_spots = record.class_id.max_capacity - record.current_bookings
