# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NhsSimpleLog(models.Model):
    _name = 'nhs.simple.log'
    _description = 'NHS API Call Log'
    _order = 'create_date desc'
    _rec_name = 'request_id'

    create_date = fields.Datetime(readonly=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user,
                              readonly=True)
    patient_id = fields.Many2one('nhs.simple.patient', string='Patient',
                                 ondelete='set null')
    nhs_number = fields.Char(string='NHS Number', readonly=True)
    request_id = fields.Char(string='Request ID', readonly=True)
    url = fields.Char(string='URL', readonly=True)
    status_code = fields.Integer(string='HTTP Status', readonly=True)
    duration_ms = fields.Integer(string='Duration (ms)', readonly=True)
    environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('integration', 'Integration'),
        ('production', 'Production'),
    ], readonly=True)
    response_body = fields.Text(string='Response', readonly=True)
    error = fields.Text(string='Error', readonly=True)
    success = fields.Boolean(compute='_compute_success', store=True)

    @api.depends('status_code')
    def _compute_success(self):
        for rec in self:
            rec.success = 200 <= (rec.status_code or 0) < 300
