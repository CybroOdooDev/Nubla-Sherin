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


class NhsDsptNewEditionWizard(models.TransientModel):
    """Wizard to clone an existing DSPT edition's structure to a new financial year."""
    _name = 'nhs.dspt.new.edition.wizard'
    _description = 'Clone a DSPT Edition to a New Year'

    source_edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Source Edition',
        required=True,
        help="The edition to clone standards/assertions/evidence from."
    )
    new_year = fields.Char(
        string='New Year',
        required=True,
        help="e.g. '2026/27'."
    )
    new_name = fields.Char(
        string='New Edition Name',
    )
    new_deadline = fields.Date(
        string='New Deadline',
    )

    def action_confirm(self):
        """Triggers the edition cloning logic and opens the form view of the new edition."""
        self.ensure_one()
        new_edition = self.source_edition_id.copy_edition(
            new_year=self.new_year,
            new_name=self.new_name,
            new_deadline=self.new_deadline,
        )
        return {
            'name': ('DSPT Edition'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.edition',
            'view_mode': 'form',
            'res_id': new_edition.id,
        }
