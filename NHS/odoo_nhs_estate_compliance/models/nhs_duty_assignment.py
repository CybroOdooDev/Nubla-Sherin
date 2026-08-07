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
from odoo.exceptions import ValidationError

class NHSDutyAssignment(models.Model):
    """Model to manage assignments of persons to statutory duty roles, disciplines, and locations."""
    _name = 'nhs.duty.assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Person ↔ Role ↔ Discipline ↔ Location'
    _order = 'person_id, duty_role_id'

    person_id = fields.Many2one('res.users', string='Person', required=True,
                                 help='The user assigned to this duty role.')
    duty_role_id = fields.Many2one('nhs.duty.role', string='Duty Role', required=True,
                                help='The statutory duty role being assigned (e.g. Duty Holder, Responsible Person).')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline',
                                help='Discipline the role applies to.')
    site_id = fields.Many2one('nhs.estate.site', string='Site', help='Scope of the assignment')
    building_id = fields.Many2one('nhs.estate.building', string='Building', help='Scope of the assignment')
    authorised_from = fields.Date(string='Authorised From',
                                  help='The date from which this duty role authorisation is effective.')
    authorised_to = fields.Date(string='Authorised To',
                                help='The date on which this duty role authorisation expires.')
    authorisation_ref = fields.Char(string='Authorisation Reference',
                                    help='The formal authorisation document or reference number.')
    competency_evidence_ids = fields.Many2many('ir.attachment', string='Competency Evidence',
                                               help='Training/authorisation evidence')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired', store=True,
                                help='Automatically set to True when the authorised_to date has passed.')
    safety_group = fields.Selection([
        ('water', 'Water Safety Group'),
        ('fire', 'Fire Safety Group'),
        ('electrical', 'Electrical Safety Group'),
        ('other', 'Other Safety Group')
    ], string='Safety Group Membership', help='Water Safety Group (and equivalent groups) membership record.')

    @api.depends('authorised_to')
    def _compute_is_expired(self):
        """Compute whether the duty assignment's authorisation has expired by comparing authorised_to against today."""
        for assignment in self:
            if assignment.authorised_to:
                assignment.is_expired = assignment.authorised_to < fields.Date.today()
            else:
                assignment.is_expired = False

    @api.depends('person_id.name', 'duty_role_id.name')
    def _compute_display_name(self):
        """Build a human-readable display name combining the person name and duty role name."""
        for assignment in self:
            person_name = assignment.person_id.name or ''
            role_name = assignment.duty_role_id.name or ''
            assignment.display_name = f"{person_name} - {role_name}"

    @api.constrains('duty_role_id', 'authorisation_ref', 'authorised_from', 'authorised_to')
    def _check_authorisation_ref(self):
        """Validate that roles requiring authorisation have all mandatory authorisation fields filled,
        and that the authorised_from date is earlier than the authorised_to date.
        """
        for assignment in self:
            if assignment.duty_role_id.requires_authorisation:
                if not assignment.authorisation_ref or not assignment.authorised_from or not assignment.authorised_to:
                    raise ValidationError(
                        f'Duty Role "{assignment.duty_role_id.name}" requires authorisation details. '
                        f'Please provide an Authorisation Reference, Authorised From Date, and Authorised To Date.')
            if assignment.authorised_from and assignment.authorised_to:
                if assignment.authorised_from >= assignment.authorised_to:
                    raise ValidationError('The Authorised From date must be earlier than the Authorised To date.')

    @api.constrains('person_id', 'duty_role_id', 'discipline_id', 'site_id', 'building_id')
    def _check_unique_assignment(self):
        """Ensure that a duplicate duty assignment does not exist for the same person, role, discipline, and
        location combination."""
        for assignment in self:
            domain = [
                ('person_id', '=', assignment.person_id.id),
                ('duty_role_id', '=', assignment.duty_role_id.id),
                ('id', '!=', assignment.id)
            ]
            if assignment.discipline_id:
                domain.append(('discipline_id', '=', assignment.discipline_id.id))
            if assignment.site_id:
                domain.append(('site_id', '=', assignment.site_id.id))
            if assignment.building_id:
                domain.append(('building_id', '=', assignment.building_id.id))
            if self.search(domain):
                raise ValidationError('This assignment already exists.')

    @api.model
    def _send_authorisation_expiry_reminders(self):
        """Scheduled action to send email reminders for duty role authorisations expiring within 30 days.
        For each expiring or expired assignment, sends the appropriate email
        template (expiring-soon or already-expired) and creates a to-do activity
        for the assigned person.
        """
        from datetime import timedelta
        today = fields.Date.today()
        warning_limit = today + timedelta(days=30)
        expiring_assignments = self.search([
            ('authorised_to', '!=', False),
            ('authorised_to', '<=', warning_limit),
        ])
        template_expiry = self.env.ref('odoo_nhs_estate_compliance.mail_template_authorisation_expiry',
                                       raise_if_not_found=False)
        template_expired = self.env.ref('odoo_nhs_estate_compliance.mail_template_authorisation_expired',
                                        raise_if_not_found=False)
        for assignment in expiring_assignments:
            is_expired = assignment.authorised_to < today
            if is_expired:
                if template_expired:
                    template_expired.send_mail(assignment.id, force_send=True)
            else:
                if template_expiry:
                    template_expiry.send_mail(assignment.id, force_send=True)
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.duty.assignment'),
                ('res_id', '=', assignment.id),
                ('user_id', '=', assignment.person_id.id),
            ])
            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                summary = "Duty Role Authorisation EXPIRED" if is_expired else "Duty Role Assignment Expiring soon"
                note = (f"Your authorisation for the role {assignment.duty_role_id.name} has EXPIRED on "
                        f"{assignment.authorised_to}.") if is_expired else (f"Your authorisation for the role "
                        f"{assignment.duty_role_id.name} expires on {assignment.authorised_to}.")
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id if activity_type else False,
                    'res_model_id': self.env['ir.model']._get_id('nhs.duty.assignment'),
                    'res_id': assignment.id,
                    'user_id': assignment.person_id.id,
                    'summary': summary,
                    'note': note,
                    'date_deadline': assignment.authorised_to or today,
                })

    @api.model
    def _check_expiry(self):
        """Master scheduled action that delegates to all expiry-checking routines.
        Calls authorisation expiry reminders, contractor insurance/accreditation
        checks, and test certificate expiry checks in sequence.
        """
        # Delegate to the respective models/methods
        self._send_authorisation_expiry_reminders()
        self.env['nhs.compliance.contractor']._check_contractor_expiry()
        self.env['nhs.compliance.test']._check_test_certificate_expiry()

    @api.model
    def get_import_templates(self):
        """Download import templates for Accountable Person assignments."""
        return [{
            'label': 'Import Template for Accountable Person',
            'template': '/odoo_nhs_estate_compliance/static/import_templates/accountable_person.xlsx',
        }]

    def action_view_documents(self):
        """Open the list/form view of documents attached to this duty assignment record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.duty.assignment'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.duty.assignment',
                'default_res_id': self.id,
            }
        }
