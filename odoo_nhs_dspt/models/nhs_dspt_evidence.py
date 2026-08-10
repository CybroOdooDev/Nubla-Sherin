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
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

EVIDENCE_STATUSES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('met', 'Met'),
    ('not_met', 'Not Met'),
    ('not_applicable', 'Not Applicable'),
]

class NhsDsptEvidence(models.Model):
    """Represents a specific evidence line on a DSPT assessment."""
    _name = 'nhs.dspt.evidence'
    _inherit = ['mail.thread']
    _description = 'DSPT Evidence Line (on an assessment)'
    _order = 'standard_id, sequence, reference'

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
        help="Owning assessment."
    )
    assertion_id = fields.Many2one(
        'nhs.dspt.assertion',
        string='Assertion Line',
        required=True,
        ondelete='cascade',
        index=True,
        help="Parent assertion line."
    )
    evidence_def_id = fields.Many2one(
        'nhs.dspt.evidence.def',
        string='Evidence Definition',
        required=True,
        ondelete='restrict',
        index=True,
        help="The evidence definition."
    )
    standard_id = fields.Many2one(
        'nhs.dspt.standard',
        string='Standard',
        related='evidence_def_id.standard_id',
        store=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        related='evidence_def_id.sequence',
        store=True,
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
    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('met', 'Standards Met'),
        ('not_met', 'Not Met'),
        ('not_applicable', 'Not Applicable'),
    ], string='Status', required=True, default='not_started', tracking=True)
    na_reason = fields.Text(
        string='N/A Reason',
        help="Required explanation if status is 'not_applicable'."
    )
    answer = fields.Text(
        string='Answer / Implementation Summary',
        help="How the organisation meets this evidence requirement."
    )
    evidence_ref = fields.Char(
        string='Evidence Reference / Location',
        help="Brief path/reference to policy or system."
    )
    linked_source = fields.Char(
        string='Linked Source',
        help="Identifies third-party integration source if applicable."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help="Supporting documentation files."
    )
    action_ids = fields.One2many(
        'nhs.dspt.action',
        'evidence_id',
        string='Improvement Actions',
        help="Actions raised to resolve this gap."
    )
    action_count = fields.Integer(
        string='Action Count',
        compute='_compute_action_count',
    )
    evidence_review_date = fields.Date(
        string='Evidence Review Date',
        tracking=True,
        help="Date this evidence was last reviewed for this assessment."
    )
    is_stale = fields.Boolean(
        string='Stale / Expired',
        compute='_compute_is_stale',
        store=True,
        help="True if the review date is older than the configured expiry period."
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

    @api.depends('action_ids')
    def _compute_action_count(self):
        """Computes the total number of improvement actions raised for this evidence gap."""
        for evidence in self:
            evidence.action_count = len(evidence.action_ids)

    @api.depends('evidence_review_date', 'status')
    def _compute_is_stale(self):
        """Computes whether the evidence is stale based on last review date and config parameters."""
        today = fields.Date.context_today(self)
        for evidence in self:
            if evidence.status == 'met' and evidence.evidence_review_date:
                months = evidence.company_id.dspt_stale_evidence_months
                expiry_limit = today - relativedelta(months=months)
                evidence.is_stale = evidence.evidence_review_date < expiry_limit
            else:
                evidence.is_stale = False

    def _check_evidence_permissions(self, vals):
        """Ensures the user has permission to modify this evidence item, enforcing locked states."""
        for evidence in self:
            if evidence.assessment_id.state in ('published', 'submitted') and not self.env.user.has_group(
                    'odoo_nhs_dspt.group_nhs_dspt_manager'):
                raise UserError((
                    "This evidence item belongs to a published/submitted assessment and is locked."
                ))
            if 'owner_id' in vals or 'status' in vals or 'answer' in vals or 'attachment_ids' in vals:
                if self.env.user.has_group('odoo_nhs_dspt.group_nhs_dspt_user'):
                    if not self.env.user.has_group('odoo_nhs_dspt.group_nhs_dspt_officer'):
                        if evidence.owner_id and evidence.owner_id != self.env.user:
                            raise UserError((
                                "You can only update evidence items that are assigned to you."
                            ))

    @api.model_create_multi
    def create(self, vals_list):
        """Creates new evidence records and recomputes status and readiness."""
        records = super().create(vals_list)
        records.mapped('assertion_id')._compute_status()
        records.mapped('assessment_id')._compute_readiness()
        return records

    def write(self, vals):
        """Overrides write to check permissions, enforce validation on N/A reasons, and trigger status updates."""
        self._check_evidence_permissions(vals)
        if vals.get('status') == 'not_applicable' and not vals.get('na_reason') and not self.na_reason:
            raise ValidationError(("You must provide an N/A Reason when marking evidence as Not Applicable."))
        result = super().write(vals)
        if 'status' in vals or 'evidence_review_date' in vals:
            self.assertion_id._compute_status()
            self.mapped('assessment_id')._compute_readiness()
        return result

    def unlink(self):
        """Overrides unlink to prevent manual deletion of evidence records."""
        raise UserError(("Manual deletion of evidence items is not allowed."
                          " They are managed via assessment generation."))

    def action_raise_action(self):
        """Opens a wizard or action to raise a new improvement action linked to this evidence gap."""
        self.ensure_one()
        return {
            'name': ('Raise Improvement Action'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.action',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assessment_id': self.assessment_id.id,
                'default_evidence_id': self.id,
                'default_owner_id': self.owner_id.id or self.env.user.id,
                'default_name': ('Resolve compliance gap for %s') % self.name,
                'raise_action_wizard': True,
            }
        }

    def action_view_actions(self):
        """Returns an action to view the improvement actions raised for this evidence gap."""
        self.ensure_one()
        return {
            'name': ('Improvement Actions'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.action',
            'view_mode': 'list,form',
            'domain': [('evidence_id', '=', self.id)],
            'context': {
                'default_evidence_id': self.id,
                'default_assessment_id': self.assessment_id.id,
                'create': self.status == 'not_met',
            },
        }

    def action_set_in_progress(self):
        """Sets the evidence status to 'in_progress'."""
        self.write({'status': 'in_progress'})

    def action_set_met(self):
        """Sets the evidence status to 'met', defaulting the review date to
        today only if one hasn't already been set."""
        for evidence in self:
            vals = {'status': 'met'}
            if not evidence.evidence_review_date:
                vals['evidence_review_date'] = fields.Date.context_today(self)
            evidence.write(vals)

    def action_set_not_met(self):
        """Sets the evidence status to 'not_met'."""
        self.write({'status': 'not_met'})

    def action_set_not_applicable(self):
        """Sets the evidence status to 'not_applicable'."""
        self.write({'status': 'not_applicable'})

    @api.model
    def _cron_recompute_stale(self):
        """Cron job to recompute the is_stale field for all active evidence items."""
        self.search([])._compute_is_stale()

    @api.model
    def get_import_templates(self):
        """Import template for seeding an assessment's answers/evidence history
        (e.g. a prior year's submission not previously held in the system)."""
        return [{
            'label': 'Import Template for DSPT Evidence Answers (History)',
            'template': '/odoo_nhs_dspt/static/import_templates/dspt_evidence_answers_import_template.xlsx',
        }]
