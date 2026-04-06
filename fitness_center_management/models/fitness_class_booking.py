# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessClassBooking(models.Model):
    _name = 'fitness.class.booking'
    _description = 'Fitness Class Booking'

    schedule_id = fields.Many2one('fitness.class.schedule', string='Schedule', required=True)
    member_id = fields.Many2one('fitness.member', string='Member', required=True)
    booking_date = fields.Date(string='Booking Date', default=fields.Date.context_today)
    state = fields.Selection([
        ('booked', 'Booked'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='booked')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(FitnessClassBooking, self).create(vals_list)
        for record in records:
            record.schedule_id._compute_bookings()
        return records
