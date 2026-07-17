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
from odoo.exceptions import UserError, ValidationError


class NhsDsptAssessment(models.Model):
    """Represents a single organisation's DSPT assessment for a specific toolkit edition."""
    _name = 'nhs.dspt.assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "An organisation's DSPT assessment for an edition"
    _order = 'year desc, id desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="e.g. 'DSPT 2025/26 — Example NHS Trust'."
    )
    edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Edition',
        required=True,
        ondelete='restrict',
        index=True,
        domain="[('state', '=', 'active')]",
        help="The DSPT edition being completed."
    )
    year = fields.Char(
        string='Year',
        related='edition_id.year',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Assessing organisation; record rules scope on it."
    )
    org_profile_id = fields.Many2one(
        'nhs.dspt.org.profile',
        string='Organisation Type',
        required=True,
        help="Organisation-type profile — filters which assertions/evidence apply."
    )
    ods_code = fields.Char(
        string='ODS Code',
        help="Organisation ODS code (soft; from the Trust suite if present,"
             " else entered directly)."
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('published', 'Published'),
        ('submitted', 'Submitted'),
    ], string='Status', required=True, default='draft', tracking=True)
    assertion_ids = fields.One2many(
        'nhs.dspt.assertion',
        'assessment_id',
        string='Assertions',
        help="Assertion lines for this assessment."
    )
    evidence_ids = fields.One2many(
        'nhs.dspt.evidence',
        'assessment_id',
        string='Evidence Items',
        help="Evidence lines."
    )
    action_ids = fields.One2many(
        'nhs.dspt.action',
        'assessment_id',
        string='Improvement Actions',
    )
    action_count = fields.Integer(
        string='Action Count',
        compute='_compute_action_count',
    )
    evidence_count = fields.Integer(
        string='Evidence Count',
        compute='_compute_action_count',
    )
    readiness_pct = fields.Float(
        string='Readiness %',
        compute='_compute_readiness',
        store=True,
        digits=(16, 1),
        help="Mandatory evidence met ÷ total mandatory applicable."
    )
    achieved_status = fields.Selection([
        ('standards_met', 'Standards Met'),
        ('plan_in_place', 'Plan in Place'),
        ('approaching', 'Approaching Standards'),
        ('not_met', 'Standards Not Met'),
    ], string='Achieved Status', compute='_compute_readiness', store=True,
        help="Computed from mandatory-item completion, or an improvement plan"
             " covering the remaining gaps.")
    gap_count = fields.Integer(
        string='Gaps',
        compute='_compute_readiness',
        store=True,
        help="Mandatory evidence items currently not met."
    )
    gap_evidence_ids = fields.One2many(
        'nhs.dspt.evidence',
        'assessment_id',
        string='Gap Evidence',
        compute='_compute_gap_evidence_ids',
        help="Mandatory evidence items currently not met."
    )
    stale_evidence_count = fields.Integer(
        string='Stale Evidence',
        compute='_compute_readiness',
        store=True,
    )
    deadline = fields.Date(
        string='Deadline',
        related='edition_id.deadline',
        store=True,
    )
    published_by_id = fields.Many2one(
        'res.users',
        string='Published By',
        readonly=True,
    )
    published_at = fields.Datetime(
        string='Published At',
        readonly=True,
    )
    submission_reference = fields.Char(
        string='Submission Reference',
        help="Reference from the NHS DSPT portal after submission."
    )
    submission_date = fields.Date(
        string='Submission Date',
    )
    prior_assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Prior Assessment',
        help="Last year's assessment, for carry-forward and comparison."
    )
    notes = fields.Text(
        string='Notes',
        help="Assessment notes/commentary."
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )


    @api.constrains('edition_id', 'org_profile_id', 'ods_code', 'company_id')
    def _check_unique_assessment(self):
        """Ensures only one assessment exists per company, edition, and ODS code."""
        for assessment in self:
            domain = [
                ('id', '!=', assessment.id),
                ('edition_id', '=', assessment.edition_id.id),
                ('org_profile_id', '=', assessment.org_profile_id.id),
                ('company_id', '=', assessment.company_id.id),
            ]
            if assessment.ods_code:
                domain.append(('ods_code', '=', assessment.ods_code))
            else:
                domain.append(('ods_code', 'in', [False, '']))

            duplicate = self.sudo().search(domain, limit=1)
            if duplicate:
                raise ValidationError(_(
                    "There is already a DSPT assessment for this organisation, edition, and ODS Code."
                ))


    @api.depends('edition_id.name', 'company_id.name')
    def _compute_name(self):
        """Computes a descriptive name for the assessment."""
        for assessment in self:
            assessment.name = _('%s — %s') % (assessment.edition_id.name or _('New Edition'),
                                                assessment.company_id.name or '')

    @api.depends('action_ids', 'evidence_ids')
    def _compute_action_count(self):
        """Computes action and evidence counts for the assessment."""
        for assessment in self:
            assessment.action_count = len(assessment.action_ids)
            assessment.evidence_count = len(assessment.evidence_ids)

    @api.depends('evidence_ids.status', 'evidence_ids.is_mandatory', 'evidence_ids.is_stale',
                 'evidence_ids.action_ids.state', 'action_ids.state')
    def _compute_readiness(self):
        """Computes the readiness percentage, gaps, and status of the assessment."""
        approaching_threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_dspt.approaching_threshold', 80))
        for assessment in self:
            mandatory = assessment.evidence_ids.filtered(
                lambda e: e.is_mandatory and e.status != 'not_applicable')
            total = len(mandatory)
            met = len(mandatory.filtered(lambda e: e.status == 'met'))
            assessment.readiness_pct = (met / total * 100.0) if total else 100.0

            gaps = mandatory.filtered(lambda e: e.status == 'not_met')
            assessment.gap_count = len(gaps)
            assessment.stale_evidence_count = len(assessment.evidence_ids.filtered('is_stale'))

            if not total or met == total:
                assessment.achieved_status = 'standards_met'
            elif gaps and all(gap.action_ids for gap in gaps):
                assessment.achieved_status = 'plan_in_place'
            elif assessment.readiness_pct >= approaching_threshold:
                assessment.achieved_status = 'approaching'
            else:
                assessment.achieved_status = 'not_met'

    @api.depends('evidence_ids.status', 'evidence_ids.is_mandatory')
    def _compute_gap_evidence_ids(self):
        """Computes the subset of mandatory evidence items currently not met."""
        for assessment in self:
            assessment.gap_evidence_ids = assessment.evidence_ids.filtered(
                lambda e: e.is_mandatory and e.status == 'not_met')

    def _check_not_locked(self):
        """Raises an error if the assessment is locked due to being published/submitted."""
        for assessment in self:
            if assessment.state in ('published', 'submitted') and not self.env.user.has_group(
                    'odoo_nhs_dspt.group_nhs_dspt_manager'):
                raise UserError(_(
                    'This assessment has been published and is locked. Ask a DSPT'
                    ' manager to re-open it before making changes.'))

    def action_generate(self):
        """Create assertion + evidence lines from the edition, filtered by the
        assessment's organisation-type profile. Safe to re-run: only adds
        lines that don't already exist (e.g. after the edition gains items)."""
        Assertion = self.env['nhs.dspt.assertion']
        Evidence = self.env['nhs.dspt.evidence']
        for assessment in self:
            assessment._check_not_locked()
            existing_assertion_defs = assessment.assertion_ids.assertion_def_id
            for standard in assessment.edition_id.standard_ids:
                for assertion_def in standard.assertion_def_ids:
                    if not assertion_def.applies_to(assessment.org_profile_id):
                        continue
                    assertion_line = assessment.assertion_ids.filtered(
                        lambda a: a.assertion_def_id == assertion_def)
                    if not assertion_line:
                        assertion_line = Assertion.create({
                            'assessment_id': assessment.id,
                            'assertion_def_id': assertion_def.id,
                        })
                    existing_evidence_defs = assertion_line.evidence_ids.evidence_def_id
                    for evidence_def in assertion_def.evidence_def_ids:
                        if evidence_def in existing_evidence_defs:
                            continue
                        if not evidence_def.applies_to(assessment.org_profile_id):
                            continue
                        Evidence.create({
                            'assessment_id': assessment.id,
                            'assertion_id': assertion_line.id,
                            'evidence_def_id': evidence_def.id,
                        })
            if assessment.state == 'draft':
                assessment.state = 'in_progress'
        return True

    def action_carry_forward(self, prior_assessment=None, carry_answers=True,
                               carry_attachments=True, carry_owners=True):
        """Pre-fill answers/evidence/owners from a prior assessment, matching
        lines by their definition's reference (stable across editions even
        when the underlying definition record is a new clone).
        Returns the number of evidence lines updated."""
        updated_count = 0
        for assessment in self:
            prior = prior_assessment or assessment.prior_assessment_id
            if not prior:
                continue
            assessment._check_not_locked()
            prior_by_ref = {e.reference: e for e in prior.evidence_ids}
            for evidence in assessment.evidence_ids:
                source = prior_by_ref.get(evidence.reference)
                if not source:
                    continue
                vals = {}
                if carry_answers:
                    vals.update({
                        'status': source.status,
                        'answer': source.answer,
                        'na_reason': source.na_reason,
                        'evidence_ref': source.evidence_ref,
                        'evidence_review_date': source.evidence_review_date,
                        'linked_source': source.linked_source,
                    })
                if carry_attachments and source.attachment_ids:
                    vals['attachment_ids'] = [(6, 0, source.attachment_ids.ids)]
                if carry_owners and source.owner_id:
                    vals['owner_id'] = source.owner_id.id
                if vals:
                    evidence.write(vals)
                    updated_count += 1
        return updated_count

    def action_recompute(self):
        """Forces recalculation of statuses, readiness, and returns a client notification.
        Compares against the values the button was clicked with (passed in via context from
        the form) rather than a fresh DB read, so the message reflects what the user was
        actually looking at, even if the screen had gone stale since the record was loaded."""
        achieved_status_labels = dict(self._fields['achieved_status'].selection)
        assertion_status_labels = dict(self.env['nhs.dspt.assertion']._fields['status'].selection)
        evidence_status_labels = dict(self.env['nhs.dspt.evidence']._fields['status'].selection)
        ctx = self.env.context
        has_client_snapshot = len(self) == 1 and 'client_gap_count' in ctx
        changes = []
        for assessment in self:
            if has_client_snapshot:
                before = (ctx.get('client_readiness_pct'), ctx.get('client_gap_count'),
                          ctx.get('client_stale_evidence_count'), ctx.get('client_achieved_status'))
            else:
                before = (assessment.readiness_pct, assessment.gap_count,
                          assessment.stale_evidence_count, assessment.achieved_status)
            assertion_before = {a.id: a.status for a in assessment.assertion_ids}
            evidence_before = {e.id: (e.status, e.is_stale) for e in assessment.evidence_ids}

            assessment.assertion_ids._compute_status()
            assessment.evidence_ids._compute_is_stale()
            assessment._compute_readiness()

            after = (assessment.readiness_pct, assessment.gap_count,
                      assessment.stale_evidence_count, assessment.achieved_status)

            item_lines = []
            for assertion in assessment.assertion_ids:
                old_status = assertion_before.get(assertion.id)
                if old_status is not None and old_status != assertion.status:
                    item_lines.append(_('  • Assertion %(ref)s %(name)s: %(before)s → %(after)s') % {
                        'ref': assertion.reference,
                        'name': assertion.name,
                        'before': assertion_status_labels.get(old_status, old_status),
                        'after': assertion_status_labels.get(assertion.status, assertion.status),
                    })
            for evidence in assessment.evidence_ids:
                old_status, old_stale = evidence_before.get(evidence.id, (None, None))
                if old_status is None:
                    continue
                bits = []
                if old_status != evidence.status:
                    bits.append(_('status %(before)s → %(after)s') % {
                        'before': evidence_status_labels.get(old_status, old_status),
                        'after': evidence_status_labels.get(evidence.status, evidence.status),
                    })
                if old_stale != evidence.is_stale:
                    bits.append(_('now stale') if evidence.is_stale else _('no longer stale'))
                if bits:
                    item_lines.append(_('  • Evidence %(ref)s %(name)s: %(detail)s') % {
                        'ref': evidence.reference,
                        'name': evidence.name,
                        'detail': ', '.join(bits),
                    })

            if before != after or item_lines:
                lines = [_(
                    '%(name)s: readiness %(before_pct).0f%% → %(after_pct).0f%%, '
                    'gaps %(before_gaps)d → %(after_gaps)d, '
                    'stale %(before_stale)d → %(after_stale)d, '
                    'status %(before_status)s → %(after_status)s') % {
                    'name': assessment.name,
                    'before_pct': before[0], 'after_pct': after[0],
                    'before_gaps': before[1], 'after_gaps': after[1],
                    'before_stale': before[2], 'after_stale': after[2],
                    'before_status': achieved_status_labels.get(before[3], before[3]),
                    'after_status': achieved_status_labels.get(after[3], after[3]),
                }]
                lines.extend(item_lines)
                changes.append('\n'.join(lines))
        if changes:
            title = _('Recomputed — changes found')
            message = '\n'.join(changes)
            notif_type = 'success'
        else:
            title = _('Recomputed')
            message = _('Everything was already up to date — no changes found.')
            notif_type = 'info'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_mark_ready(self):
        """Transitions the assessment state to 'ready'."""
        for assessment in self:
            assessment._check_not_locked()
            assessment.state = 'ready'

    def action_publish(self):
        """Transitions the assessment state to 'published' and locks it.
        Blocks if any improvement action is not yet completed/verified."""
        for assessment in self:
            assessment._check_not_locked()
            open_actions = assessment.action_ids.filtered(
                lambda a: a.state not in ('completed', 'verified'))
            if open_actions:
                raise UserError(_(
                    'All improvement actions must be Completed or Verified before'
                    ' publishing. %(count)d action(s) still open: %(names)s') % {
                    'count': len(open_actions),
                    'names': ', '.join(open_actions.mapped('name')),
                })
            assessment.write({
                'state': 'published',
                'published_by_id': self.env.user.id,
                'published_at': fields.Datetime.now(),
            })
        return True

    def action_submit(self):
        """Transitions the assessment state to 'submitted' once a reference is entered."""
        for assessment in self:
            if not assessment.submission_reference:
                raise UserError(_('Enter the submission reference from the NHS DSPT portal first.'))
            assessment.write({
                'state': 'submitted',
                'submission_date': assessment.submission_date or fields.Date.context_today(self),
            })
        return True

    def action_reopen(self):
        """Re-opens a published/submitted assessment (manager only)."""
        for assessment in self:
            if not self.env.user.has_group('odoo_nhs_dspt.group_nhs_dspt_manager'):
                raise UserError(_('Only a DSPT manager can re-open a published assessment.'))
            assessment.message_post(body=_('Assessment re-opened by %s.') % self.env.user.name)
            assessment.state = 'in_progress'
        return True

    def action_view_evidence(self):
        """Returns an action to view the assessment's evidence library."""
        self.ensure_one()
        return {
            'name': _('Evidence Library'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.evidence',
            'view_mode': 'list,form',
            'domain': [('assessment_id', '=', self.id)],
            'context': {'default_assessment_id': self.id},
        }

    def action_view_actions(self):
        """Returns an action to view the assessment's improvement actions."""
        self.ensure_one()
        return {
            'name': _('Improvement Actions'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.action',
            'view_mode': 'list,form',
            'domain': [('assessment_id', '=', self.id)],
            'context': {'default_assessment_id': self.id},
        }

    @api.model
    def _cron_deadline_reminders(self):
        """Nightly reminder as an edition's deadline approaches, to assessment
        owners and to the DSPT manager group."""
        lead_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_dspt.deadline_reminder_days', 30))
        today = fields.Date.context_today(self)
        template = self.env.ref('odoo_nhs_dspt.mail_template_dspt_deadline_reminder', raise_if_not_found=False)
        if not template:
            return
        assessments = self.search([
            ('deadline', '!=', False),
            ('state', 'not in', ['published', 'submitted']),
        ])
        for assessment in assessments:
            days_left = (assessment.deadline - today).days
            if 0 <= days_left <= lead_days:
                template.send_mail(assessment.id, force_send=False)

    @api.model
    def _default_report_assessments(self):
        """Fallback recordset for a report triggered from a menu with no
        record selected: the current company's assessment for the active
        edition, if any."""
        assessment = self.search([
            ('company_id', '=', self.env.company.id),
            ('edition_id.state', '=', 'active'),
        ], limit=1, order='id desc')
        return assessment or self.search([('company_id', '=', self.env.company.id)], limit=1, order='id desc')

    @api.model
    def get_dspt_dashboard_data(self):
        """Aggregated metrics for the client-side Readiness Dashboard, for the
        current company's most relevant assessment (the active edition's, if
        one exists; otherwise the latest overall)."""
        assessment = self.search([
            ('company_id', '=', self.env.company.id),
            ('edition_id.state', '=', 'active'),
        ], limit=1, order='id desc')
        if not assessment:
            assessment = self.search([
                ('company_id', '=', self.env.company.id),
            ], limit=1, order='id desc')
        if not assessment:
            return {'has_assessment': False}

        today = fields.Date.context_today(self)
        days_left = (assessment.deadline - today).days if assessment.deadline else False
        if days_left is False:
            rag = 'none'
        elif days_left < 0:
            rag = 'behind'
        elif assessment.readiness_pct >= 100:
            rag = 'on_track'
        elif days_left <= 30 and assessment.readiness_pct < 80:
            rag = 'behind'
        elif days_left <= 90 and assessment.readiness_pct < 60:
            rag = 'at_risk'
        else:
            rag = 'on_track'

        standard_stats = []
        for standard in assessment.assertion_ids.standard_id:
            evidence = assessment.evidence_ids.filtered(
                lambda e, std=standard: e.standard_id == std and
                                        e.is_mandatory and e.status != 'not_applicable')
            total = len(evidence) or 1
            met = len(evidence.filtered(lambda e: e.status == 'met'))
            standard_stats.append({
                'id': standard.id,
                'name': standard.name,
                'rate': round(met / total * 100.0, 1),
            })
        standard_stats.sort(key=lambda s: s['rate'])

        owner_stats = []
        for owner in assessment.evidence_ids.owner_id:
            owned = assessment.evidence_ids.filtered(lambda e, u=owner: e.owner_id == u)
            outstanding = owned.filtered(lambda e: e.status not in ('met', 'not_applicable'))
            owner_stats.append({
                'id': owner.id,
                'name': owner.name,
                'total': len(owned),
                'outstanding': len(outstanding),
            })
        owner_stats.sort(key=lambda o: -o['outstanding'])

        overdue_actions = assessment.action_ids.filtered('is_overdue')

        return {
            'has_assessment': True,
            'assessment_id': assessment.id,
            'assessment_name': assessment.name,
            'readiness_pct': round(assessment.readiness_pct, 1),
            'achieved_status': assessment.achieved_status,
            'gap_count': assessment.gap_count,
            'stale_evidence_count': assessment.stale_evidence_count,
            'overdue_action_count': len(overdue_actions),
            'deadline': fields.Date.to_string(assessment.deadline) if assessment.deadline else '',
            'days_left': days_left,
            'rag': rag,
            'standard_stats': standard_stats,
            'owner_stats': owner_stats[:8],
        }
