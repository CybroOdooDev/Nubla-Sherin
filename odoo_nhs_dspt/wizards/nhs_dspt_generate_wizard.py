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
from odoo import api, fields, models


class NhsDsptGenerateWizard(models.TransientModel):
    """Wizard to generate assessment lines (assertions and evidence) for a DSPT assessment."""
    _name = 'nhs.dspt.generate.wizard'
    _description = 'Generate DSPT Assertion & Evidence Lines'

    assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Assessment',
        required=True,
    )
    edition_id = fields.Many2one(
        related='assessment_id.edition_id',
        string='Edition',
    )
    org_profile_id = fields.Many2one(
        related='assessment_id.org_profile_id',
        string='Organisation Type',
    )
    existing_line_count = fields.Integer(
        string='Existing Evidence Lines',
        compute='_compute_existing_line_count',
    )

    @api.depends('assessment_id')
    def _compute_existing_line_count(self):
        """Computes the number of existing evidence lines on the assessment."""
        for wizard in self:
            wizard.existing_line_count = len(wizard.assessment_id.evidence_ids)

    def action_confirm(self):
        """Generates the assessment lines and closes the wizard."""
        self.ensure_one()
        self.assessment_id.action_generate()
        return {'type': 'ir.actions.act_window_close'}
