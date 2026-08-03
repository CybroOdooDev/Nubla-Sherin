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
from odoo.exceptions import UserError


class NhsShortlistWizardLine(models.TransientModel):
    _name = 'nhs.shortlist.wizard.line'
    _description = 'Shortlisting wizard line'

    wizard_id = fields.Many2one('nhs.shortlist.wizard', string='Wizard', ondelete='cascade')
    application_id = fields.Many2one('nhs.application', string='Application', required=True)
    candidate_id = fields.Many2one(
        related='application_id.candidate_id', string='Candidate', readonly=True)
    shortlist_score = fields.Float(
        related='application_id.shortlist_score', string='Score', readonly=True)
    outcome = fields.Selection([
        ('shortlisted', 'Shortlisted'),
        ('not_shortlisted', 'Not Shortlisted'),
        ('hold', 'Hold'),
    ], string='Outcome', required=True, default='hold')
    reason = fields.Char(string='Reason')


class NhsShortlistWizard(models.TransientModel):
    """Bulk-decide shortlist outcomes across every application currently
    being shortlisted for a vacancy."""
    _name = 'nhs.shortlist.wizard'
    _description = 'Shortlisting wizard'

    vacancy_id = fields.Many2one('nhs.vacancy', string='Vacancy', required=True)
    line_ids = fields.One2many('nhs.shortlist.wizard.line', 'wizard_id', string='Applications')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        vacancy_id = res.get('vacancy_id') or self.env.context.get('default_vacancy_id')
        if vacancy_id:
            applications = self.env['nhs.application'].search([
                ('vacancy_id', '=', vacancy_id),
                ('stage', 'in', ('received', 'shortlisting')),
            ])
            res['line_ids'] = [(0, 0, {
                'application_id': app.id,
                'outcome': app.shortlist_outcome or 'hold',
                'reason': app.shortlist_reason,
            }) for app in applications]
        return res

    def action_apply(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.outcome == 'not_shortlisted' and not line.reason:
                raise UserError(_(
                    'A reason is required for every application marked Not Shortlisted.'))
            line.application_id.write({
                'shortlist_outcome': line.outcome,
                'shortlist_reason': line.reason,
                'stage': 'shortlisting',
            })
            line.application_id.action_shortlist_decide()
        return {'type': 'ir.actions.act_window_close'}
