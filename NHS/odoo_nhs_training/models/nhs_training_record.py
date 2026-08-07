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
from odoo import  api, fields, models
from odoo.exceptions import UserError, ValidationError

METHODS = [
    ('elearning', 'e-Learning'),
    ('classroom', 'Classroom'),
    ('assessment', 'Assessment'),
    ('self_cert', 'Self-Certification'),
    ('other', 'Other'),
]

STATUSES = [
    ('compliant', 'Compliant'),
    ('due_soon', 'Due Soon'),
    ('expired', 'Expired'),
    ('failed', 'Failed'),
]


class NhsTrainingRecord(models.Model):
    _name = 'nhs.training.record'
    _inherit = ['mail.thread']
    _description = 'A completed training event and its expiry'
    _order = 'expiry_date, id'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. 'Fire Safety — J. Smith — 2026'."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company that owns this training record, defaulted to the current company."
    )
    member_id = fields.Many2one(
        'nhs.workforce.member',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help="Who completed the training."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Team / Department',
        related='member_id.org_unit_id',
        store=True,
        help="Team of the member, for grouping/filtering."
    )
    member_required_subject_ids = fields.Many2many(
        'nhs.training.subject',
        related='member_id.required_subject_ids',
        string='Member Required Subjects',
        help="Technical field used to restrict the Subject choice to the member's"
             " resolved requirement set."
    )
    subject_id = fields.Many2one(
        'nhs.training.subject',
        string='Subject',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help="Subject (and level) completed. Restricted to the member's required"
             " subjects where the member has a resolved requirement set."
    )
    completion_date = fields.Date(
        string='Completion Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Date completed. Cannot be in the future."
    )
    method = fields.Selection(
        METHODS,
        string='Method',
        help="How the training was delivered."
    )
    provider = fields.Char(
        string='Provider',
        help="Training provider / source."
    )
    frequency_months = fields.Integer(
        string='Refresh Interval (Months)',
        compute='_compute_frequency_months',
        store=True,
        readonly=False,
        help="Effective refresh interval (requirement override, else the subject default)."
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry_date',
        store=True,
        readonly=False,
        tracking=True,
        help="completion_date + effective refresh interval. Blank for one-off subjects."
             " Overridable via Manual Expiry."
    )
    expiry_override = fields.Date(
        string='Manual Expiry',
        help="Set when a certificate states a specific expiry date."
    )
    status = fields.Selection(
        STATUSES,
        string='Status',
        compute='_compute_status',
        store=True,
        tracking=True,
        help="compliant / due_soon / expired / failed. One-off subjects are always compliant"
             " once done. A Result of Fail always forces the status to failed, regardless of"
             " expiry, until a later completion supersedes it."
    )
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', help="Pass/fail result, where relevant.")
    certificate_ref = fields.Char(
        string='Certificate Reference',
        help="Reference/serial number printed on the certificate or evidence document."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Certificate / Evidence',
        help="Uploaded certificates or other evidence supporting this completion."
    )
    is_latest = fields.Boolean(
        string='Latest Completion',
        compute='_compute_is_latest',
        store=True,
        help="True if this is the most recent completion of this subject for this member."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag; records are archived rather than deleted to preserve the"
             " compliance evidence trail."
    )

    @api.depends('subject_id', 'member_id', 'completion_date')
    def _compute_name(self):
        """Build the display name from the subject, member and completion year."""
        for rec in self:
            year = rec.completion_date.year if rec.completion_date else ''
            rec.name = ' — '.join(filter(None, [
                rec.subject_id.complete_name, rec.member_id.name, str(year) or None]))

    @api.depends('subject_id', 'member_id')
    def _compute_frequency_months(self):
        """Resolve the effective refresh interval for the record's member/subject pair."""
        for rec in self:
            if rec.member_id and rec.subject_id:
                rec.frequency_months = rec.member_id.get_effective_frequency_months(rec.subject_id)
            else:
                rec.frequency_months = rec.subject_id.default_frequency_months

    @api.depends('completion_date', 'frequency_months', 'expiry_override', 'subject_id.is_one_off')
    def _compute_expiry_date(self):
        """Derive the expiry date from completion date and frequency, honouring manual overrides."""
        for rec in self:
            if rec.expiry_override:
                rec.expiry_date = rec.expiry_override
            elif rec.subject_id.is_one_off or not rec.frequency_months:
                rec.expiry_date = False
            elif rec.completion_date:
                rec.expiry_date = rec.completion_date + relativedelta(months=rec.frequency_months)
            else:
                rec.expiry_date = False

    @api.depends('expiry_date', 'subject_id.is_one_off', 'subject_id.default_lead_days', 'result')
    def _compute_status(self):
        """Determine compliant/due_soon/expired/failed status from the expiry date and result."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.result == 'fail':
                rec.status = 'failed'
            elif rec.subject_id.is_one_off or not rec.expiry_date:
                rec.status = 'compliant'
            elif rec.expiry_date < today:
                rec.status = 'expired'
            elif (rec.expiry_date - today).days <= (rec.subject_id.default_lead_days or 0):
                rec.status = 'due_soon'
            else:
                rec.status = 'compliant'

    @api.depends('member_id', 'subject_id', 'completion_date')
    def _compute_is_latest(self):
        """Flag whether this is the most recent completion of the subject for the member."""
        for rec in self:
            siblings = self.search([
                ('member_id', '=', rec.member_id.id),
                ('subject_id', '=', rec.subject_id.id),
            ], order='completion_date desc', limit=1)
            rec.is_latest = siblings.id == rec.id if siblings else False

    def _recompute_sibling_is_latest(self):
        """is_latest is stored, but a new/changed record doesn't automatically
        invalidate its siblings' cached value — recompute the whole member+subject
        group explicitly whenever membership of that group changes."""
        pairs = {(rec.member_id.id, rec.subject_id.id) for rec in self}
        siblings = self.browse()
        for member_id, subject_id in pairs:
            siblings |= self.search([('member_id', '=', member_id), ('subject_id', '=', subject_id)])
        siblings._compute_is_latest()

    @api.model_create_multi
    def create(self, vals_list):
        """Create records then recompute the latest-completion flag for their siblings."""
        records = super().create(vals_list)
        records._recompute_sibling_is_latest()
        return records

    def write(self, vals):
        """Update records then recompute the latest-completion flag if member/subject/date changed."""
        result = super().write(vals)
        if 'member_id' in vals or 'subject_id' in vals or 'completion_date' in vals:
            self._recompute_sibling_is_latest()
        return result

    @api.constrains('completion_date')
    def _check_completion_date_not_future(self):
        """Reject completion dates set in the future."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.completion_date and rec.completion_date > today:
                raise ValidationError(('The completion date cannot be in the future.'))

    def unlink(self):
        """Block deletion; training records must be archived instead."""
        raise UserError((
            'Training records cannot be deleted, to preserve the compliance evidence trail.'
            ' Archive the record instead.'))

    @api.model
    def _cron_recompute_status(self):
        """Scheduled recomputation of status for all training records."""
        self.search([])._compute_status()

    @api.model
    def get_import_templates(self):
        """Return the import template metadata for training completions."""
        return [{
            'label': 'Import Template for Training Completions',
            'template': '/odoo_nhs_training/static/import_templates/training_completions_import_template.xlsx',
        }]

    @api.model
    def _cron_send_reminders(self):
        """Nightly reminders to members (and to-do activities for their manager) for
        completions that are due soon or have expired."""
        due_soon_template = self.env.ref(
            'odoo_nhs_training.mail_template_training_due_soon', raise_if_not_found=False)
        expired_template = self.env.ref(
            'odoo_nhs_training.mail_template_training_expired', raise_if_not_found=False)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for rec in self.search([('status', 'in', ('due_soon', 'expired')), ('is_latest', '=', True)]):
            template = due_soon_template if rec.status == 'due_soon' else expired_template
            if template and (rec.member_id.email or (rec.member_id.user_id and rec.member_id.user_id.email)):
                template.send_mail(rec.id, force_send=True)
            manager = rec.org_unit_id.manager_id
            if manager and activity_type:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'nhs.training.record'),
                    ('res_id', '=', rec.id),
                    ('user_id', '=', manager.id),
                ])
                if not existing:
                    self.env['mail.activity'].create({
                        'activity_type_id': activity_type.id,
                        'res_model_id': self.env['ir.model']._get_id('nhs.training.record'),
                        'res_id': rec.id,
                        'user_id': manager.id,
                        'summary': ('%s is %s') % (rec.name, rec.status.replace('_', ' ').upper()),
                        'note': ('%(member)s — %(subject)s expires %(expiry)s.') % {
                            'member': rec.member_id.name,
                            'subject': rec.subject_id.complete_name,
                            'expiry': rec.expiry_date,
                        },
                        'date_deadline': rec.expiry_date or fields.Date.context_today(self),
                    })
