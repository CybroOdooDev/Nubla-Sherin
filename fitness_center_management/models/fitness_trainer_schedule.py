# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessTrainerSchedule(models.Model):
    _name = 'fitness.trainer.schedule'
    _description = 'Fitness Trainer Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Schedule Name', compute='_compute_name', store=True)
    trainer_id = fields.Many2one('fitness.trainer', string='Trainer', required=True)
    date = fields.Date(string='Date', required=True)
    start_time = fields.Float(string='Start Time (Hours)', required=True)
    end_time = fields.Float(string='End Time (Hours)', required=True)
    session_id = fields.Many2one('fitness.training.session', string='Assigned Session')
    member_id = fields.Many2one('fitness.member', string='Personal Training for Member')
    
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked')
    ], string='Status', default='available')

    @api.depends('trainer_id', 'date')
    def _compute_name(self):
        for record in self:
            if record.trainer_id and record.date:
                record.name = f"{record.trainer_id.name} - {record.date}"
            else:
                record.name = "New Schedule"
