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

EVIDENCE_STATUSES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('met', 'Met'),
    ('not_met', 'Not Met'),
    ('not_applicable', 'Not Applicable'),
]


class NhsDsptEvidence(models.Model):
    _name = 'nhs.dspt.evidence'
    _inherit = ['mail.thread']
    _description = 'DSPT Evidence Line (on an assessment)'
    _order = 'assertion_id, evidence_def_id'

    name = fields.Char(
        string='Evidence Item',
        related='evidence_def_id.name',
        store=True,
    )
    reference = fields.Char(
        string='Reference',
        related='evidence_def_id.reference',
        store=True,
    )
    assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Assessment',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning assessment (denormalised for search)."
    )
    assertion_id = fields.Many2one(
        'nhs.dspt.assertion',
        string='Assertion',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning assertion line."
    )
    standard_id = fields.Many2one(
        'nhs.dspt.standard',
        string='Standard',
        related='assertion_id.standard_id',
        store=True,
    )
    evidence_def_id = fields.Many2one(
        'nhs.dspt.evidence.def',
        string='Evidence Definition',
        required=True,
        ondelete='restrict',
        index=True,
        help="The evidence-item definition."
    )
    is_mandatory = fields.Boolean(
        string='Mandatory',
        related='evidence_def_id.is_mandatory',
        store=True,
    )
    guidance = fields.Text(
        string='Guidance',
        related='evidence_def_id.guidance',
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        tracking=True,
        help="Responsible owner."
    )
    status = fields.Selection(
        EVIDENCE_STATUSES,
        string='Status',
        required=True,
        default='not_started',
        tracking=True,
    )
    na_reason = fields.Char(
        string='Not-Applicable Reason',
        help="Justification when marked not applicable."
    )
    answer = fields.Text(
        string='Answer',
        help="The response/answer the toolkit requires."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Evidence Documents',
        help="Supporting documents: policies, certificates, screenshots, reports."
    )
    evidence_ref = fields.Char(
        string='Evidence Reference',
        help="Reference/description of the evidence."
    )
    evidence_review_date = fields.Date(
        string='Evidence Review Date',
        help="When this evidence should next be refreshed."
    )
    is_stale = fields.Boolean(
        string='Stale',
        compute='_compute_is_stale',
        store=True,
        help="True once the evidence review date has passed."
    )
    linked_source = fields.Char(
        string='Linked Source',
        help="Optional soft reference to evidence held in another suite module"
             " (e.g. a training-compliance % or an incident record), where installed."
    )
    action_ids = fields.One2many(
        'nhs.dspt.action',
        'evidence_id',
        string='Improvement Actions',
        help="Improvement actions raised from this gap."
    )
    action_count = fields.Integer(
        string='Action Count',
        compute='_compute_action_count',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='assessment_id.company_id',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.depends('evidence_review_date')
    def _compute_is_stale(self):
        today = fields.Date.context_today(self)
        for evidence in self:
            evidence.is_stale = bool(evidence.evidence_review_date and evidence.evidence_review_date < today)

    @api.depends('action_ids')
    def _compute_action_count(self):
        for evidence in self:
            evidence.action_count = len(evidence.action_ids)

    @api.onchange('status')
    def _onchange_status_na_reason(self):
        if self.status != 'not_applicable':
            self.na_reason = False

    def write(self, vals):
        for evidence in self:
            if evidence.assessment_id.state in ('published', 'submitted') and not self.env.user.has_group(
                    'odoo_nhs_dspt.group_nhs_dspt_manager'):
                raise UserError(_(
                    'This assessment has been published and is locked. Ask a DSPT'
                    ' manager to re-open it before editing evidence.'))
        result = super().write(vals)
        if 'status' in vals or 'evidence_review_date' in vals:
            self.assertion_id._compute_status()
            self.mapped('assessment_id')._compute_readiness()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped('assertion_id')._compute_status()
        records.mapped('assessment_id')._compute_readiness()
        return records

    def action_raise_action(self):
        """Raise an improvement action from this gap (spec 4.6)."""
        self.ensure_one()
        return {
            'name': _('Raise Improvement Action'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.action',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assessment_id': self.assessment_id.id,
                'default_evidence_id': self.id,
                'default_owner_id': self.owner_id.id,
                'default_name': _('Close gap: %s') % self.name,
            },
        }

    def action_view_actions(self):
        self.ensure_one()
        return {
            'name': _('Improvement Actions'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.action',
            'view_mode': 'list,form',
            'domain': [('evidence_id', '=', self.id)],
            'context': {'default_evidence_id': self.id, 'default_assessment_id': self.assessment_id.id},
        }

    def action_set_in_progress(self):
        for record in self:
            record.write({'status': 'in_progress'})

    def action_set_met(self):
        for record in self:
            record.write({'status': 'met'})

    def action_set_not_met(self):
        for record in self:
            record.write({'status': 'not_met'})

    def action_set_not_applicable(self):
        for record in self:
            record.write({'status': 'not_applicable'})

    @api.model
    def _cron_recompute_stale(self):
        self.search([])._compute_is_stale()
