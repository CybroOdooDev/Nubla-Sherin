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

    training_due_soon_days = fields.Integer(
        string='Due Soon Window (Days)',
        default=60,
        config_parameter='odoo_nhs_training.due_soon_days',
        help="Default number of days before expiry at which a professional registration"
             " is flagged 'expiring soon' (subjects carry their own window)."
    )
    training_compliance_target = fields.Integer(
        string='Compliance Target (%)',
        default=85,
        config_parameter='odoo_nhs_training.compliance_target',
        help="The board-set compliance target (commonly 85% or 90%) that member, team"
             " and organisation compliance is measured against."
    )
    training_digest_recipients = fields.Char(
        string='Digest Recipients',
        config_parameter='odoo_nhs_training.digest_recipients',
        help="Comma-separated fallback email addresses for the weekly compliance digest."
    )
