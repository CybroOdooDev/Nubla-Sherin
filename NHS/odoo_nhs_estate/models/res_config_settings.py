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
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    condition_rollup = fields.Selection([
        ('worst', 'Worst Grade (Default)'),
        ('weighted', 'Weighted Average')
    ], string='Condition Roll-up Rule',
        default='worst',
        config_parameter='odoo_nhs_estate.condition_rollup',
        help="Determines how the overall condition grade is calculated from the six facet ratings "
             "(Physical, Statutory/Safety, Functional, Utilisation, Quality/Environment, and Energy Performance).\n\n"
             "- **Worst Grade (Default)**: Selects the poorest grade across all facets (conservative approach). "
             "If any facet is rated D (Poor), the overall grade becomes D regardless of other ratings.\n\n"
             "- **Weighted Average**: Calculates an equal-weighted average of all facet grades. "
             "Provides a balanced assessment where each facet contributes equally (weight = 1). "
             "The numeric average is then mapped back to a grade (A, B, C, or D).\n\n"
             "This setting applies globally across the system and can be changed at any time."
    )
