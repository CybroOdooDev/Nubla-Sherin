# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhs_ods_contact_email = fields.Char(
        string='ODS Contact Email',
        config_parameter='nhs_ods_sync.contact_email',
        help="Sent as part of the User-Agent header so NHS Digital can identify the client.",
    )
    nhs_ods_timeout = fields.Integer(
        string='Request Timeout (seconds)',
        config_parameter='nhs_ods_sync.timeout',
        default=30,
    )
    nhs_ods_rate_per_sec = fields.Float(
        string='Rate Limit (req/sec)',
        config_parameter='nhs_ods_sync.rate_per_sec',
        default=5.0,
    )
    nhs_ods_default_mode = fields.Selection([
        ('live', 'Live'),
        ('dry_run', 'Dry Run'),
    ], string='Default Sync Mode',
        config_parameter='nhs_ods_sync.default_mode',
        default='live',
    )
    nhs_ods_auto_resolve_trivial = fields.Boolean(
        string='Auto-resolve trivial diffs (whitespace/casing)',
        config_parameter='nhs_ods_sync.auto_resolve_trivial',
        default=False,
    )
    nhs_ods_conflict_group_id = fields.Many2one(
        'res.groups',
        string='Conflict Notification Group',
        help="Users in this group receive an activity when a new conflict is detected.",
    )

    def action_test_ods_connection(self):
        self.ensure_one()
        wizard = self.env['nhs.ods.test.connection.wizard'].create({})
        return wizard.action_open()
