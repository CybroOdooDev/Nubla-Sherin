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
from odoo import _, api, fields, models


class NhsDsptCarryForwardWizard(models.TransientModel):
    """Wizard to carry forward answers, owners, and attachments from a prior DSPT assessment."""
    _name = 'nhs.dspt.carry.forward.wizard'
    _description = 'Carry Forward Prior DSPT Assessment'

    assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Assessment',
        required=True,
    )
    prior_assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Carry Forward From',
        required=True,
        domain="[('id', '!=', assessment_id), ('company_id', '=', company_id), "
               "('org_profile_id', '=', org_profile_id), ('ods_code', '=', ods_code)]",
        help="Usually last year's assessment for the same organisation."
    )
    company_id = fields.Many2one(
        related='assessment_id.company_id',
    )
    org_profile_id = fields.Many2one(
        related='assessment_id.org_profile_id',
    )
    ods_code = fields.Char(
        related='assessment_id.ods_code',
    )
    carry_answers = fields.Boolean(
        string='Carry Forward Answers & Status',
        default=True,
    )
    carry_attachments = fields.Boolean(
        string='Carry Forward Evidence Attachments',
        default=True,
    )
    carry_owners = fields.Boolean(
        string='Carry Forward Owners',
        default=True,
    )

    @api.onchange('assessment_id')
    def _onchange_assessment_id(self):
        """Pre-fills the prior assessment if configured on the current assessment."""
        if self.assessment_id.prior_assessment_id:
            self.prior_assessment_id = self.assessment_id.prior_assessment_id

    def action_confirm(self):
        """Executes the carry forward logic on the target assessment."""
        self.ensure_one()
        updated_count = self.assessment_id.action_carry_forward(
            prior_assessment=self.prior_assessment_id,
            carry_answers=self.carry_answers,
            carry_attachments=self.carry_attachments,
            carry_owners=self.carry_owners,
        )
        if not self.assessment_id.prior_assessment_id:
            self.assessment_id.prior_assessment_id = self.prior_assessment_id
        if updated_count:
            title = _('Carried Forward')
            message = _('%(count)d evidence item(s) updated from %(source)s.') % {
                'count': updated_count,
                'source': self.prior_assessment_id.name,
            }
            notif_type = 'success'
        else:
            title = _('Nothing Carried Forward')
            message = _(
                'No matching evidence references were found in %(source)s, or it has no '
                'evidence yet. Make sure you selected the correct earlier assessment.'
            ) % {'source': self.prior_assessment_id.name}
            notif_type = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
            },
        }
