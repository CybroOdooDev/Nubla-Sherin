# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class FitnessSubscription(models.Model):
    _name = 'fitness.subscription'
    _description = 'Fitness Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Subscription Reference', required=True, copy=False, readonly=True, default='New')
    member_id = fields.Many2one('fitness.member', string='Member', required=True, tracking=True)
    plan_id = fields.Many2one('fitness.membership.plan', string='Plan', required=True, tracking=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='End Date', compute='_compute_end_date', store=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('renewed', 'Renewed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Payment Status', compute='_compute_payment_status', store=True, tracking=True)
    total_amount = fields.Float(string='Total Amount', related='plan_id.price', readonly=True, store=True)
    invoice_ids = fields.Many2many('account.move', string='Invoices', readonly=True)

    @api.depends('invoice_ids.payment_state')
    def _compute_payment_status(self):
        for record in self:
            if not record.invoice_ids:
                record.payment_status = 'unpaid'
            else:
                if all(inv.payment_state in ('paid', 'in_payment') for inv in record.invoice_ids):
                    record.payment_status = 'paid'
                elif any(inv.payment_state in ('paid', 'in_payment') for inv in record.invoice_ids):
                    record.payment_status = 'partial'
                else:
                    record.payment_status = 'unpaid'

    @api.depends('start_date', 'plan_id.duration_months')
    def _compute_end_date(self):
        for record in self:
            if record.start_date and record.plan_id:
                record.end_date = record.start_date + relativedelta(months=record.plan_id.duration_months)
            else:
                record.end_date = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fitness.subscription') or 'New'
        return super(FitnessSubscription, self).create(vals_list)
