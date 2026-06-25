# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#############################################################################
from odoo import fields, models


class NhsComplaintTimescale(models.Model):
    _name = 'nhs.complaint.timescale'
    _description = 'Complaint Response-Timescale Preset'
    _order = 'working_days'

    name = fields.Char(string='Preset Name', required=True,
                       help='e.g. Standard (40 working days)')
    working_days = fields.Integer(string='Working Days', required=True,
                                  help='Default number of working days for the agreed response deadline.')
    complexity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('major', 'Major'),
    ], string='Complexity', help='Suggested mapping from complaint severity.')
    active = fields.Boolean(default=True, string='Active')
    description = fields.Text(string='Notes',
                              help='Optional notes about when this timescale preset should be applied.')
