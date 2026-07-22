# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsGovernanceCommitteeType(models.Model):
    _name = 'nhs.governance.committee.type'
    _description = 'NHS Governance Committee Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, help="Display name for the committee type.")
    code = fields.Char(required=True, help="Technical code used to classify committee and board records.")
    sequence = fields.Integer(default=10, help="Ordering sequence for committee type lists.")
    active = fields.Boolean(default=True, help="Archive flag for committee types no longer used.")


class NhsGovernanceInterestCategory(models.Model):
    _name = 'nhs.governance.interest.category'
    _description = 'NHS Governance Interest Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, help="Display name for the declaration-of-interest category.")
    code = fields.Char(required=True, help="Technical code for interest category reporting.")
    sequence = fields.Integer(default=10, help="Ordering sequence for interest category lists.")
    active = fields.Boolean(default=True, help="Archive flag for categories no longer used.")


class NhsGovernanceAssuranceLine(models.Model):
    _name = 'nhs.governance.assurance.line'
    _description = 'NHS Governance Assurance Line'
    _order = 'sequence, name'

    name = fields.Char(required=True, help="Display name for the assurance line.")
    code = fields.Selection([
        ('first', 'First Line - Operational Management'),
        ('second', 'Second Line - Oversight Functions'),
        ('third', 'Third Line - Independent Assurance'),
    ], required=True, help="Three-lines-of-defence classification used for BAF assurances.")
    sequence = fields.Integer(default=10, help="Ordering sequence for assurance-line lists.")
    active = fields.Boolean(default=True, help="Archive flag for assurance lines no longer used.")
