# -*- coding: utf-8 -*-
from odoo import models, fields

class FitnessBranch(models.Model):
    _name = 'fitness.branch'
    _description = 'Fitness Center Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Branch Name', required=True, tracking=True)
    code = fields.Char(string='Branch Code')
    manager_id = fields.Many2one('res.users', string='Branch Manager', tracking=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    member_ids = fields.One2many('fitness.member', 'branch_id', string='Members')
    class_ids = fields.One2many('fitness.class', 'branch_id', string='Classes')
