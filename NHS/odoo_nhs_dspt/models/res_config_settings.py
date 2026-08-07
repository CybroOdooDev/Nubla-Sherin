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


class ResConfigSettings(models.TransientModel):
    """Inherits configuration settings to manage DSPT-specific global parameters."""
    _inherit = 'res.config.settings'

    dspt_deadline_reminder_days = fields.Integer(
        string='Deadline Reminder Lead Time (Days)',
        related='company_id.dspt_deadline_reminder_days',
        readonly=False,
        help="Send deadline reminders once an edition's deadline is within"
             " this many days."
    )
    dspt_stale_evidence_months = fields.Integer(
        string='Stale Evidence Age (Months)',
        related='company_id.dspt_stale_evidence_months',
        readonly=False,
        help="Informational default review cycle for evidence without an"
             " explicit review date."
    )
    dspt_approaching_threshold = fields.Integer(
        string='Approaching Standards Threshold (%)',
        related='company_id.dspt_approaching_threshold',
        readonly=False,
        help="Readiness % above which an incomplete assessment is considered"
             " 'Approaching Standards' rather than 'Standards Not Met'."
    )
