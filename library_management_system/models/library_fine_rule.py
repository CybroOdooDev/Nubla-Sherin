# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Nublasherin k (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
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



