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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    """Extends company with per-organisation DSPT settings, so each company
    managing its own DSPT (spec 4.12) can set its own thresholds."""
    _inherit = 'res.company'

    dspt_deadline_reminder_days = fields.Integer(
        string='DSPT Deadline Reminder Lead Time (Days)',
        default=30,
        help="Send deadline reminders once an edition's deadline is within"
             " this many days."
    )
    dspt_stale_evidence_months = fields.Integer(
        string='DSPT Stale Evidence Age (Months)',
        default=12,
        help="Evidence is flagged stale once its review date is older than"
             " this many months."
    )
    dspt_approaching_threshold = fields.Integer(
        string='DSPT Approaching Standards Threshold (%)',
        default=80,
        help="Readiness % above which an incomplete assessment is considered"
             " 'Approaching Standards' rather than 'Standards Not Met'."
    )
