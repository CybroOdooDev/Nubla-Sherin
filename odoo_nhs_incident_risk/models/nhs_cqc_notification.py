from odoo import fields, models


class NhsCqcNotificationType(models.Model):
    _name = 'nhs.cqc.notification.type'
    _description = 'CQC Statutory Notification Type'
    _order = 'name'

    name = fields.Char(string='Notification Type', required=True)
    statutory_basis = fields.Char(string='Statutory Basis',
                                  help='e.g. Regulation 16, 17, or 18')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)


class NhsCqcNotification(models.Model):
    _name = 'nhs.cqc.notification'
    _description = 'CQC Statutory Notification Record'
    _inherit = ['mail.thread']
    _order = 'id desc'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict')
    notification_type_id = fields.Many2one('nhs.cqc.notification.type',
                                           string='Notification Type', required=True)
    statutory_basis = fields.Char(related='notification_type_id.statutory_basis',
                                  string='Statutory Basis', readonly=True)
    state = fields.Selection([
        ('required', 'Required'),
        ('submitted', 'Submitted'),
        ('not_required', 'Not Required'),
    ], string='Status', required=True, default='required', tracking=True)
    justification = fields.Text(string='Justification',
                                help='Required when state = Not Required.')
    submitted_at = fields.Datetime(string='Submitted At')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By')
    cqc_reference = fields.Char(string='CQC Reference')
