# -*- coding: utf-8 -*-
from odoo import models, fields


class NhsOdsFieldProvenance(models.Model):
    _name = 'nhs.ods.field.provenance'
    _description = 'Tracks the source (manual vs ODS) of each field on each NHS Trust'
    _order = 'trust_id, field_name'

    trust_id = fields.Many2one(
        'nhs.trust',
        string='Trust',
        required=True,
        ondelete='cascade',
        index=True,
    )
    field_name = fields.Char(
        string='Field (technical)',
        required=True,
        index=True,
        help="Technical field name e.g. 'name', 'phone'.",
    )
    source = fields.Selection([
        ('manual', 'Manual Edit'),
        ('ods', 'ODS Sync'),
        ('unknown', 'Unknown'),
    ], string='Source', required=True, default='unknown')
    last_updated_at = fields.Datetime(
        string='Last Updated At',
        required=True,
        default=fields.Datetime.now,
    )
    last_updated_by_user_id = fields.Many2one(
        'res.users',
        string='Last Updated By',
        help="User who set the value (manual sources only).",
    )
    last_sync_run_id = fields.Many2one(
        'nhs.ods.sync.run',
        string='Last Sync Run',
        ondelete='set null',
        help="Sync run that set the value (ODS sources only).",
    )
    auto_update = fields.Boolean(
        string='Auto Update',
        default=True,
        help="When False, the sync engine will always raise a conflict instead of auto-updating.",
    )

    _trust_field_uniq = models.Constraint(
        'unique(trust_id, field_name)',
        'One provenance row per field per trust.',
    )
