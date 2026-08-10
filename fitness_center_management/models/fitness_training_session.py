# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FitnessTrainingSession(models.Model):
    _name = 'fitness.training.session'
    _description = 'Fitness Training Session (Live/Predefined)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Session Title', required=True, tracking=True)
    session_type = fields.Selection([
        ('live', 'Live Video Call'),
        ('predefined', 'Predefined Video')
    ], string='Session Type', required=True, default='predefined', tracking=True)
    
    trainer_id = fields.Many2one('fitness.trainer', string='Trainer')
    video_url = fields.Char(string='Video/Meeting URL')
    start_time = fields.Datetime(string='Scheduled Start Time')
    duration = fields.Float(string='Duration (Hours)')
    description = fields.Html(string='Description')

    member_ids = fields.Many2many('fitness.member', string='Registered Members')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Ongoing/Active'),
        ('completed', 'Completed')
    ], string='Status', default='draft', tracking=True)

    def action_schedule(self):
        for record in self:
            record.state = 'scheduled'

    def action_start(self):
        for record in self:
            record.state = 'active'
            
    def action_complete(self):
        for record in self:
            record.state = 'completed'
