# -*- coding: utf-8 -*-
from odoo import models, fields


class NhsOdsRoleMapping(models.Model):
    _name = 'nhs.ods.role.mapping'
    _description = 'Map ODS role codes to NHS Trust type'
    _order = 'sequence, role_code'
    _rec_name = 'role_code'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="When an org has multiple roles the lowest-sequence matching mapping wins.",
    )
    role_code = fields.Char(
        string='ODS Role Code',
        required=True,
        index=True,
        help="ODS role code e.g. 'RO197'.",
    )
    role_name = fields.Char(
        string='Role Name',
        required=True,
        help="Human-readable role name e.g. 'NHS Trust'.",
    )
    trust_type_id = fields.Many2one(
        'nhs.trust.type',
        string='Trust Type',
        required=True,
        help="The nhs.trust.type to assign when this role is the primary role.",
    )
    health_system = fields.Selection([
        ('nhs_england', 'NHS England'),
        ('nhs_scotland', 'NHS Scotland'),
        ('nhs_wales', 'NHS Wales'),
        ('hsc_ni', 'HSC Northern Ireland'),
        ('both', 'All Nations'),
    ], string='Health System', required=True,
        help="Which health system this role belongs to.",
    )
    creates_trust = fields.Boolean(
        string='Creates Trust',
        default=True,
        help="When True, the sync engine will create a new nhs.trust if no match is found. "
             "Set False for roles like ICB (RO165) where we match but never create.",
    )
    active = fields.Boolean(default=True)

    _role_code_uniq = models.Constraint('unique(role_code)', 'Each ODS role code may only appear once in the mapping table.')
