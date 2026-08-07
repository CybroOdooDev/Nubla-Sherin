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
from odoo import  fields, models

class ResConfigSettings(models.TransientModel):
    """Extension of Odoo configuration settings to manage estates compliance system-wide parameters."""
    _inherit = 'res.config.settings'

    compliance_due_soon_days = fields.Integer(string='Due Soon Window (Days)',
                        default=14,
                        config_parameter='odoo_nhs_estate_compliance.due_soon_days',
                        help='Number of days before a due date at which a compliance item is flagged as "due soon".')
    compliance_escalation_threshold = fields.Integer(string='Escalation Threshold (Days)',
                            default=30,
                            config_parameter='odoo_nhs_estate_compliance.escalation_threshold',
                            help='Number of days an item must be overdue before it is escalated to the Duty Holder.')
    compliance_digest_recipients = fields.Char(string='Digest Recipients',
                                    config_parameter='odoo_nhs_estate_compliance.digest_recipients',
                                    help='Comma-separated email addresses that receive the weekly compliance digest.')
