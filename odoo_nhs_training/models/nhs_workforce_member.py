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
from odoo.orm.identifiers import NewId

COMPLIANCE_STATUSES = [
    ('compliant', 'Compliant'),
    ('at_risk', 'At Risk'),
    ('non_compliant', 'Non-Compliant'),
]

STATUS_LABELS = {
    'compliant': 'Compliant',
    'due_soon': 'Due Soon',
    'expired': 'Expired',
    'not_done': 'Not Done',
    'exempt': 'Exempt',
}


class NhsWorkforceMemberComplianceLine(models.Model):
    _name = 'nhs.workforce.member.compliance.line'
    _description = 'Workforce Member Compliance Line'
    _order = 'subject_name'

    member_id = fields.Many2one(
        'nhs.workforce.member',
        string='Member',
        ondelete='cascade',
        index=True
    )
    subject_id = fields.Many2one(
        'nhs.training.subject',
        string='Subject'
    )
    subject_name = fields.Char(
        related='subject_id.name',
        string='Subject Name',
        store=True
    )
    status = fields.Selection([
        ('compliant', 'Compliant'),
        ('due_soon', 'Due Soon'),
        ('expired', 'Expired'),
        ('not_done', 'Not Done'),
        ('exempt', 'Exempt'),
    ], string='Status')
    expiry_date = fields.Date(string='Expiry')


class NhsWorkforceMember(models.Model):
    _name = 'nhs.workforce.member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A member of staff for training-compliance purposes (data-minimised)'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        help="Member name."
    )
    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Staff/member reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Team / Department',
        tracking=True,
        index=True,
        help="Team/department the member works in."
    )
    post_id = fields.Many2one(
        'nhs.establishment.post',
        string='Post',
        tracking=True,
        domain="[('status', '=', 'active')]",
        help="The post they occupy; inherits its training requirement profile."
             " Only active posts are offered."
    )
    staff_group_id = fields.Many2one(
        'nhs.staff.group',
        string='Staff Group',
        tracking=True,
        help="Staff group, defaulted from the post, or set directly."
    )
    requirement_profile_id = fields.Many2one(
        'nhs.requirement.profile',
        string='Requirement Profile',
        tracking=True,
        help="Effective requirement profile. Defaults from the post, overridable."
    )
    user_id = fields.Many2one(
        'res.users',
        string='Related User',
        help="Optional link for portal self-view. Not required."
    )
    employee_id = fields.Reference(
        selection=[('hr.employee', 'Employee')],
        string='Employee',
        help="Optional soft link to an HR employee record, if the HR module happens to"
             " be installed. This module does not depend on HR and never requires it."
    )
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.context_today,
        help="Employment/assignment start; drives the new-starter induction prompt."
    )
    is_leaver = fields.Boolean(
        string='Leaver',
        tracking=True,
        help="Left — retained for history, excluded from live compliance."
    )
    requirement_line_ids = fields.One2many(
        'nhs.training.requirement',
        'member_id',
        string='Individual Overrides',
        help="Individual-level added or waived requirements for this member."
    )
    record_ids = fields.One2many(
        'nhs.training.record',
        'member_id',
        string='Training Records',
        help="Their training completions."
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count',
    )
    registration_ids = fields.One2many(
        'nhs.registration',
        'member_id',
        string='Professional Registrations',
        help="Their professional registrations."
    )
    registration_count = fields.Integer(
        string='Registration Count',
        compute='_compute_registration_count',
    )
    required_subject_count = fields.Integer(
        string='Required Subjects',
        compute='_compute_compliance',
        store=True,
        help="Number of subjects (excluding exempt) currently required of this member."
    )
    compliant_subject_count = fields.Integer(
        string='Compliant Subjects',
        compute='_compute_compliance',
        store=True,
    )
    expired_subject_count = fields.Integer(
        string='Expired Subjects',
        compute='_compute_compliance',
        store=True,
    )
    compliance_pct = fields.Float(
        string='Compliance %',
        compute='_compute_compliance',
        store=True,
        digits=(16, 1),
        help="% of required subjects (excluding exempt/not-applicable) currently in date."
    )
    compliance_status = fields.Selection(
        COMPLIANCE_STATUSES,
        string='Compliance Status',
        compute='_compute_compliance',
        store=True,
        help="compliant / at_risk / non_compliant against the configured target."
    )
    compliance_line_ids = fields.One2many(
        'nhs.workforce.member.compliance.line',
        'member_id',
        string='Required & Status',
        help="Each required subject with its current status and expiry."
    )
    required_subject_ids = fields.Many2many(
        'nhs.training.subject',
        compute='_compute_required_subject_ids',
        string='Required Subjects (Set)',
        help="The subjects resolved from this member's profile/staff-group/individual"
             " overrides — used to restrict the Subject choice when recording training."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    def _compute_record_count(self):
        for member in self:
            member.record_count = len(member.record_ids)

    def _compute_registration_count(self):
        for member in self:
            member.registration_count = len(member.registration_ids)

    @api.onchange('post_id')
    def _onchange_post_id(self):
        for member in self:
            if member.post_id:
                member.org_unit_id = member.post_id.org_unit_id
                member.staff_group_id = member.post_id.staff_group_id
                member.requirement_profile_id = member.post_id.training_requirement_profile_id
            else:
                member.org_unit_id = False
                member.staff_group_id = False
                member.requirement_profile_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.workforce.member') or 'New'
            if vals.get('post_id'):
                post = self.env['nhs.establishment.post'].browse(vals['post_id'])
                if post:
                    if not vals.get('org_unit_id'):
                        vals['org_unit_id'] = post.org_unit_id.id
                    if not vals.get('staff_group_id'):
                        vals['staff_group_id'] = post.staff_group_id.id
                    if 'requirement_profile_id' not in vals:
                        vals['requirement_profile_id'] = post.training_requirement_profile_id.id
        members = super().create(vals_list)
        members._prompt_induction_training()
        return members

    def write(self, vals):
        if 'post_id' in vals:
            if vals.get('post_id'):
                post = self.env['nhs.establishment.post'].browse(vals['post_id'])
                if post:
                    if 'org_unit_id' not in vals:
                        vals['org_unit_id'] = post.org_unit_id.id
                    if 'staff_group_id' not in vals:
                        vals['staff_group_id'] = post.staff_group_id.id
                    if 'requirement_profile_id' not in vals:
                        vals['requirement_profile_id'] = post.training_requirement_profile_id.id
            else:
                if 'org_unit_id' not in vals:
                    vals['org_unit_id'] = False
                if 'staff_group_id' not in vals:
                    vals['staff_group_id'] = False
                if 'requirement_profile_id' not in vals:
                    vals['requirement_profile_id'] = False
        return super().write(vals)

    def _prompt_induction_training(self):
        induction_subjects = self.env['nhs.training.subject'].search([
            ('is_one_off', '=', True), ('active', '=', True),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type or not induction_subjects:
            return
        for member in self:
            member.activity_schedule(
                activity_type_id=activity_type.id,
                summary=_('New starter — arrange induction training'),
                note=_('Arrange induction/mandatory training for %s (%s).') % (
                    member.name, ', '.join(induction_subjects.mapped('name'))),
            )

    def get_requirement_lines(self):
        """Resolve the effective set of required subjects for each member in self.

        Returns a dict member_id -> list of dicts:
            {subject, frequency_months, lead_days, is_mandatory, exempt,
             exemption_reason, exemption_review_date}
        combining profile requirements, staff-group requirements and
        individual-level add/waive overrides.
        """
        today = fields.Date.context_today(self)
        result = {}
        for member in self:
            lines = {}
            sources = self.env['nhs.training.requirement']
            if member.requirement_profile_id:
                sources |= member.requirement_profile_id.requirement_ids
            if member.staff_group_id:
                sources |= self.env['nhs.training.requirement'].search([
                    ('staff_group_id', '=', member.staff_group_id.id),
                    ('active', '=', True),
                ])
            for req in sources.filtered(lambda r: r.active):
                if req.effective_from and req.effective_from > today:
                    continue
                lines[req.subject_id.id] = {
                    'subject': req.subject_id,
                    'frequency_months': req.frequency_months_override or req.subject_id.default_frequency_months,
                    'lead_days': req.subject_id.default_lead_days,
                    'is_mandatory': req.is_mandatory,
                    'exempt': False,
                    'exemption_reason': False,
                    'exemption_review_date': False,
                }
            for override in member.requirement_line_ids.filtered(lambda r: r.active):
                if override.effective_from and override.effective_from > today:
                    continue
                if override.override_type == 'add':
                    lines[override.subject_id.id] = {
                        'subject': override.subject_id,
                        'frequency_months': override.frequency_months_override or override.subject_id.default_frequency_months,
                        'lead_days': override.subject_id.default_lead_days,
                        'is_mandatory': override.is_mandatory,
                        'exempt': False,
                        'exemption_reason': False,
                        'exemption_review_date': False,
                    }
                elif override.override_type == 'waive':
                    line = lines.get(override.subject_id.id) or {
                        'subject': override.subject_id,
                        'frequency_months': override.subject_id.default_frequency_months,
                        'lead_days': override.subject_id.default_lead_days,
                        'is_mandatory': override.is_mandatory,
                    }
                    line.update({
                        'exempt': True,
                        'exemption_reason': override.exemption_reason,
                        'exemption_review_date': override.exemption_review_date,
                    })
                    lines[override.subject_id.id] = line
            result[member.id] = list(lines.values())
        return result

    def get_effective_frequency_months(self, subject):
        """Effective refresh interval (months) for `subject` for this single member."""
        self.ensure_one()
        for line in self.get_requirement_lines()[self.id]:
            if line['subject'].id == subject.id:
                return line['frequency_months']
        return subject.default_frequency_months

    def _subject_status(self, subject, lead_days, exempt):
        """Status for one required subject, given the member's latest record."""
        self.ensure_one()
        if exempt:
            return 'exempt'
        latest = self.record_ids.filtered(lambda r: r.subject_id.id == subject.id)
        latest = latest.sorted('completion_date', reverse=True)[:1]
        if not latest:
            return 'not_done'
        return latest.status

    @api.depends('record_ids', 'record_ids.status', 'record_ids.completion_date',
                 'requirement_profile_id', 'staff_group_id', 'requirement_line_ids',
                 'requirement_line_ids.active', 'is_leaver')
    def _compute_compliance(self):
        target = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.compliance_target', 85))
        lines_by_member = self.get_requirement_lines()
        for member in self:
            lines = lines_by_member.get(member.id, [])
            required = 0
            compliant = 0
            expired = 0
            
            for line in lines:
                status = member._subject_status(line['subject'], line['lead_days'], line['exempt'])
                if status == 'exempt':
                    pass
                else:
                    required += 1
                    if status in ('compliant', 'due_soon'):
                        compliant += 1
                    if status == 'expired':
                        expired += 1
                
            member.required_subject_count = required
            member.compliant_subject_count = compliant
            member.expired_subject_count = expired
            member.compliance_pct = (compliant / required * 100.0) if required else 100.0
            if member.is_leaver:
                member.compliance_status = 'compliant'
            elif member.compliance_pct >= target:
                member.compliance_status = 'compliant'
            elif member.compliance_pct >= target - 15:
                member.compliance_status = 'at_risk'
            else:
                member.compliance_status = 'non_compliant'

            # Sync compliance lines
            if isinstance(member.id, NewId):
                commands = [(5, 0, 0)]
                for line in lines:
                    status = member._subject_status(line['subject'], line['lead_days'], line['exempt'])
                    latest = member.record_ids.filtered(lambda r: r.subject_id.id == line['subject'].id)
                    latest = latest.sorted('completion_date', reverse=True)[:1]
                    expiry_date = latest.expiry_date if latest else False
                    commands.append((0, 0, {
                        'subject_id': line['subject'].id,
                        'status': status,
                        'expiry_date': expiry_date,
                    }))
                member.compliance_line_ids = commands
            else:
                existing_lines = self.env['nhs.workforce.member.compliance.line'].search([
                    ('member_id', '=', member.id)
                ])
                existing_by_subject = {l.subject_id.id: l for l in existing_lines}
                to_delete = existing_lines
                new_vals_list = []
                
                for line in lines:
                    status = member._subject_status(line['subject'], line['lead_days'], line['exempt'])
                    latest = member.record_ids.filtered(lambda r: r.subject_id.id == line['subject'].id)
                    latest = latest.sorted('completion_date', reverse=True)[:1]
                    expiry_date = latest.expiry_date if latest else False
                    
                    vals = {
                        'member_id': member.id,
                        'subject_id': line['subject'].id,
                        'status': status,
                        'expiry_date': expiry_date,
                    }
                    
                    if line['subject'].id in existing_by_subject:
                        existing_line = existing_by_subject[line['subject'].id]
                        if (existing_line.status != status or 
                            existing_line.expiry_date != expiry_date):
                            existing_line.write({
                                'status': status,
                                'expiry_date': expiry_date,
                            })
                        to_delete -= existing_line
                    else:
                        new_vals_list.append(vals)
                
                if to_delete:
                    to_delete.unlink()
                if new_vals_list:
                    self.env['nhs.workforce.member.compliance.line'].create(new_vals_list)
                
                # Update the One2many field with the correct active database records
                member.compliance_line_ids = self.env['nhs.workforce.member.compliance.line'].search([
                    ('member_id', '=', member.id)
                ])

    @api.depends('requirement_profile_id', 'requirement_profile_id.requirement_ids',
                 'staff_group_id', 'requirement_line_ids', 'requirement_line_ids.active')
    def _compute_required_subject_ids(self):
        lines_by_member = self.get_requirement_lines()
        for member in self:
            subjects = self.env['nhs.training.subject']
            for line in lines_by_member.get(member.id, []):
                subjects |= line['subject']
            member.required_subject_ids = subjects

    def action_record_training(self):
        self.ensure_one()
        return {
            'name': _('Record Training'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.record',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_member_id': self.id,
                'default_completion_date': fields.Date.context_today(self),
            },
        }

    def action_view_records(self):
        self.ensure_one()
        return {
            'name': _('Training Records'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.record',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_registrations(self):
        self.ensure_one()
        return {
            'name': _('Professional Registrations'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.registration',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def is_training_compliant(self):
        """Stable API for other workforce modules (Staff Bank / e-Rostering) to check
        whether a member can safely be rostered: fully in-date on required training
        and current on any professional registration."""
        self.ensure_one()
        if self.expired_subject_count:
            return False
        lapsed_registration = self.registration_ids.filtered(lambda r: r.status == 'lapsed')
        return not lapsed_registration

    @api.model
    def _cron_recompute_compliance(self):
        self.env['nhs.training.record']._cron_recompute_status()
        self.env['nhs.registration']._cron_recompute_status()
        self.search([])._compute_compliance()
        self.env['nhs.org.unit'].search([])._compute_team_compliance()

    @api.model
    def get_training_matrix_data(self, org_unit_id=False):
        """Data for the signature Training Matrix client action: members (rows) x
        required subjects (columns), colour-coded by status."""
        domain = [('is_leaver', '=', False)]
        if org_unit_id:
            domain.append(('org_unit_id', 'child_of', org_unit_id))
        members = self.search(domain, order='name')
        lines_by_member = members.get_requirement_lines()
        subjects = self.env['nhs.training.subject']
        for lines in lines_by_member.values():
            subjects |= self.env['nhs.training.subject'].browse([l['subject'].id for l in lines])
        subjects = subjects.sorted(key=lambda s: (s.name, s.level or ''))

        rows = []
        for member in members:
            cells = {}
            for line in lines_by_member.get(member.id, []):
                status = member._subject_status(line['subject'], line['lead_days'], line['exempt'])
                latest = member.record_ids.filtered(lambda r: r.subject_id.id == line['subject'].id)
                latest = latest.sorted('completion_date', reverse=True)[:1]
                cells[line['subject'].id] = {
                    'status': status,
                    'label': STATUS_LABELS.get(status, status),
                    'record_id': latest.id if latest else False,
                    'expiry_date': fields.Date.to_string(latest.expiry_date) if latest and latest.expiry_date else '',
                }
            rows.append({
                'id': member.id,
                'name': member.name,
                'org_unit': member.org_unit_id.name or '',
                'post': member.post_id.job_title or '',
                'compliance_pct': round(member.compliance_pct, 1),
                'cells': cells,
            })
        return {
            'subjects': [{'id': s.id, 'name': s.complete_name} for s in subjects],
            'members': rows,
        }

    @api.model
    def get_training_dashboard_metrics(self):
        """Aggregated metrics for the client-side Compliance Dashboard."""
        target = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.compliance_target', 85))
        members = self.search([('is_leaver', '=', False)])
        total_members = len(members)
        compliant = len(members.filtered(lambda m: m.compliance_status == 'compliant'))
        at_risk = len(members.filtered(lambda m: m.compliance_status == 'at_risk'))
        non_compliant = len(members.filtered(lambda m: m.compliance_status == 'non_compliant'))
        overall_rate = (sum(members.mapped('compliant_subject_count'))
                         / sum(members.mapped('required_subject_count')) * 100.0) \
            if sum(members.mapped('required_subject_count')) else 100.0

        subject_stats = []
        Record = self.env['nhs.training.record']
        for subject in self.env['nhs.training.subject'].search([('active', '=', True)]):
            reqs = self.env['nhs.training.requirement'].search([
                ('subject_id', '=', subject.id), ('active', '=', True)])
            if not reqs:
                continue
            recs = Record.search([('subject_id', '=', subject.id), ('is_latest', '=', True)])
            total = len(recs) or 1
            compliant_recs = len(recs.filtered(lambda r: r.status in ('compliant', 'due_soon')))
            subject_stats.append({
                'id': subject.id, 'name': subject.complete_name,
                'rate': round(compliant_recs / total * 100.0, 1),
            })
        subject_stats.sort(key=lambda s: s['rate'])

        team_stats = []
        for unit in self.env['nhs.org.unit'].search([('team_required_count', '>', 0)]):
            team_stats.append({
                'id': unit.id, 'name': unit.complete_name,
                'rate': round(unit.team_compliance_pct, 1),
            })
        team_stats.sort(key=lambda t: t['rate'])

        due_soon = Record.search([('status', '=', 'due_soon'), ('is_latest', '=', True)], order='expiry_date')
        expired = Record.search([('status', '=', 'expired'), ('is_latest', '=', True)], order='expiry_date')
        lapsed_registrations = self.env['nhs.registration'].search([('status', '=', 'lapsed')])

        return {
            'overall_rate': round(overall_rate, 1),
            'target': target,
            'total_members': total_members,
            'compliant': compliant,
            'at_risk': at_risk,
            'non_compliant': non_compliant,
            'weakest_subjects': subject_stats[:8],
            'weakest_teams': team_stats[:8],
            'due_soon_count': len(due_soon),
            'expired_count': len(expired),
            'lapsed_registration_count': len(lapsed_registrations),
            'due_soon_planner': [{
                'id': r.id, 'member': r.member_id.name, 'subject': r.subject_id.complete_name,
                'team': r.org_unit_id.name or '', 'expiry_date': fields.Date.to_string(r.expiry_date),
            } for r in due_soon[:15]],
            'expired_register': [{
                'id': r.id, 'member': r.member_id.name, 'subject': r.subject_id.complete_name,
                'team': r.org_unit_id.name or '', 'expiry_date': fields.Date.to_string(r.expiry_date),
            } for r in expired[:15]],
        }

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template for Workforce Members',
            'template': '/odoo_nhs_training/static/import_templates/workforce_members_import_template.xlsx',
        }]
