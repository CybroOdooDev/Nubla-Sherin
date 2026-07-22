# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsBafAssurance(models.Model):
    _name = 'nhs.baf.assurance'
    _description = 'NHS BAF Assurance'
    _order = 'date desc, id desc'

    risk_id = fields.Many2one(
        'nhs.baf.risk',
        required=True,
        ondelete='cascade',
        help="Principal BAF risk this assurance supports.",
    )
    company_id = fields.Many2one(
        related='risk_id.company_id',
        store=True,
        help="Owning company inherited from the BAF risk.",
    )
    name = fields.Char(required=True, help="Assurance item, such as audit report, review or performance data.")
    line_of_defence = fields.Selection([
        ('first', 'First Line'),
        ('second', 'Second Line'),
        ('third', 'Third Line'),
    ], required=True, default='first', help="Three-lines-of-defence category for this assurance.")
    source = fields.Char(help="Source of the assurance, for example internal audit, external review or performance data.")
    rating = fields.Selection([
        ('positive', 'Positive'),
        ('partial', 'Partial'),
        ('negative', 'Negative'),
    ], default='partial', help="Assessment of the assurance evidence.")
    date = fields.Date(help="Date the assurance was obtained or reported.")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'nhs_baf_assurance_attachment_rel',
        'assurance_id',
        'attachment_id',
        help="Evidence files supporting this assurance.",
    )
