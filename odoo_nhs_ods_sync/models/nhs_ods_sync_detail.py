# -*- coding: utf-8 -*-
from odoo import models, fields


class NhsOdsSyncDetail(models.Model):
    _name = 'nhs.ods.sync.detail'
    _description = 'Per-organisation sync result'
    _order = 'sync_run_id desc, ods_code'

    sync_run_id = fields.Many2one(
        'nhs.ods.sync.run',
        string='Sync Run',
        required=True,
        ondelete='cascade',
        index=True,
    )
    ods_code = fields.Char(string='ODS Code', required=True)
    ods_organisation_id = fields.Many2one(
        'nhs.ods.organisation',
        string='ODS Cache Entry',
        ondelete='set null',
    )
    outcome = fields.Selection([
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('unchanged', 'Unchanged'),
        ('conflict', 'Conflict'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
        ('would_update', 'Would Update (dry run)'),
    ], string='Outcome', required=True)
    trust_id = fields.Many2one(
        'nhs.trust',
        string='Trust',
        ondelete='set null',
    )
    icb_id = fields.Many2one(
        'nhs.icb',
        string='ICB',
        ondelete='set null',
    )
    changed_fields = fields.Char(
        string='Changed Fields',
        help="Comma-separated list of nhs.trust fields modified.",
    )
    conflict_ids = fields.One2many(
        'nhs.ods.sync.conflict',
        'sync_detail_id',
        string='Conflicts',
    )
    error_message = fields.Text(string='Error Message')
    skip_reason = fields.Char(string='Skip Reason')
    duration_ms = fields.Integer(string='Duration (ms)')
    diff_json = fields.Text(
        string='Diff (JSON)',
        help="For dry-run would_update rows: JSON representation of what would change.",
    )
