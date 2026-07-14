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
    _inherit = 'res.config.settings'

    dspt_deadline_reminder_days = fields.Integer(
        string='Deadline Reminder Lead Time (Days)',
        config_parameter='odoo_nhs_dspt.deadline_reminder_days',
        default=30,
        help="Send deadline reminders once an edition's deadline is within"
             " this many days."
    )
    dspt_stale_evidence_months = fields.Integer(
        string='Stale Evidence Age (Months)',
        config_parameter='odoo_nhs_dspt.stale_evidence_months',
        default=12,
        help="Informational default review cycle for evidence without an"
             " explicit review date."
    )
    dspt_approaching_threshold = fields.Integer(
        string='Approaching Standards Threshold (%)',
        config_parameter='odoo_nhs_dspt.approaching_threshold',
        default=80,
        help="Readiness % above which an incomplete assessment is considered"
             " 'Approaching Standards' rather than 'Standards Not Met'."
    )
