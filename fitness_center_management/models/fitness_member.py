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
