# -*- coding: utf-8 -*-
from odoo import models,fields


class LibraryFineRule(models.Model):
    """ Class for Storing library fine rule """
    _name = 'library.fine.rule'
    _description = "Library Fine Rule"

    name = fields.Char("Rule Name", required=True)
    fine_type = fields.Selection([
        ('late_return', 'Late Return'),
        ('lost', 'Lost Book'),
        ('damage', 'Book Damage'),
    ], string="Fine Type", required=True)
    amount_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('per_day', 'Per Day (Late Return)'),
        ('percentage', 'percentage')
    ], default='fixed', required=True)
    fine_amount = fields.Float("Fine Amount", required=True)
    active = fields.Boolean(default=True)



