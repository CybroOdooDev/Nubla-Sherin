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
from datetime import timedelta

class NHSComplianceContractor(models.Model):
    """Model to manage external contractors and their statutory accreditations and insurance policies."""
    _name = 'nhs.compliance.contractor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contractor & Accreditation'

    name = fields.Char(
        string='Contractor Name',
        required=True,
        help='The registered name of the external contractor.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Optional link to the contact record'
    )
    discipline_ids = fields.Many2many(
        'nhs.compliance.discipline',
        string='Disciplines',
        help='Disciplines they are engaged for'
    )
    accreditation_ids = fields.One2many(
        'nhs.contractor.accreditation.line',
        'contractor_id',
        string='Accreditations',
        help='Accreditations held by the contractor with their respective expiry dates (e.g., NICEIC, Gas Safe, LEEA)'
    )
    nearest_expiry_date = fields.Date(
        string='Nearest Expiry Date',
        compute='_compute_nearest_expiry',
        store=True,
        help='The earliest expiry date among all accreditations held by this contractor. '
             'Automatically calculated from accreditation lines.'
    )
    nearest_expiring_accreditation = fields.Char(
        string='Nearest Expiring Accreditation',
        compute='_compute_nearest_expiry',
        store=True,
        help='The accreditation code that expires soonest among all accreditations '
             'held by this contractor.'
    )
    insurance_expiry = fields.Date(
        string='Insurance Expiry',
        help='Date on which the contractor\'s insurance policy expires.'
    )
    visit_ids = fields.One2many(
        'nhs.contractor.visit',
        'contractor_id',
        string='Visits',
        help='All site visits recorded for this contractor.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive the contractor without deleting the record.'
    )
    is_insurance_expired = fields.Boolean(
        string='Insurance Expired',
        compute='_compute_is_expired',
        store=True,
        help='Automatically set to True when the insurance expiry date is in the past.'
    )
    is_accreditation_expired = fields.Boolean(
        string='Accreditation Expired',
        compute='_compute_is_expired',
        store=True,
        help='Automatically set to True when any accreditation has expired.'
    )

    @api.depends('accreditation_ids.expiry_date')
    def _compute_nearest_expiry(self):
        """Compute the nearest expiry date and corresponding accreditation code.
        Finds the accreditation with the earliest expiry date among all accreditation
        lines for this contractor. The result is stored for efficient filtering and
        display in list views.
        """
        for contractor in self:
            valid_lines = contractor.accreditation_ids.filtered(lambda l: l.expiry_date)
            if valid_lines:
                nearest = min(valid_lines, key=lambda l: l.expiry_date)
                contractor.nearest_expiry_date = nearest.expiry_date
                contractor.nearest_expiring_accreditation = nearest.accreditation_id.code
            else:
                contractor.nearest_expiry_date = False
                contractor.nearest_expiring_accreditation = False

    @api.depends('insurance_expiry', 'accreditation_ids.is_expired')
    def _compute_is_expired(self):
        """Compute whether the contractor's insurance and/or accreditations have expired.
        Compares insurance expiry date against today's date and checks if any
        accreditation line is marked as expired. Sets the corresponding boolean
        flags accordingly.
        """
        today = fields.Date.today()
        for contractor in self:
            if contractor.insurance_expiry and contractor.insurance_expiry < today:
                contractor.is_insurance_expired = True
            else:
                contractor.is_insurance_expired = False
            if contractor.accreditation_ids:
                contractor.is_accreditation_expired = any(
                    line.is_expired for line in contractor.accreditation_ids
                )
            else:
                contractor.is_accreditation_expired = False

    def _check_insurance_expiry(self, today, warning_limit, dh_users, dh_emails):
        """Check and notify about insurance expiry."""
        expiring_contractors = self.search([
            ('insurance_expiry', '!=', False),
            ('insurance_expiry', '<=', warning_limit)
        ])
        template_ins = self.env.ref(
            'odoo_nhs_estate_compliance.mail_template_contractor_insurance_expiry',
            raise_if_not_found=False
        )
        template_ins_expired = self.env.ref(
            'odoo_nhs_estate_compliance.mail_template_contractor_insurance_expired',
            raise_if_not_found=False
        )
        for contractor in expiring_contractors:
            recipient_email = contractor.partner_id.email or dh_emails
            if contractor.insurance_expiry < today:
                if template_ins_expired and recipient_email:
                    template_ins_expired.send_mail(
                        contractor.id,
                        email_values={'email_to': recipient_email},
                        force_send=True
                    )
            elif contractor.insurance_expiry <= warning_limit:
                if template_ins and recipient_email:
                    template_ins.send_mail(
                        contractor.id,
                        email_values={'email_to': recipient_email},
                        force_send=True
                    )
            self._create_expiry_activity(contractor, 'Insurance', contractor.insurance_expiry, dh_users)

    @api.model
    def _check_contractor_expiry(self):
        """Scheduled action to check contractor insurance and accreditation expiry."""
        from datetime import timedelta
        today = fields.Date.today()
        warning_limit = today + timedelta(days=30)
        dh_assignments = self.env['nhs.duty.assignment'].search([('duty_role_id.code', '=', 'DH')])
        dh_users = dh_assignments.mapped('person_id') or self.env.user
        dh_emails = ",".join([u.email for u in dh_users if u.email])
        self._check_insurance_expiry(today, warning_limit, dh_users, dh_emails)
        self._check_accreditation_expiry(today, warning_limit, dh_users, dh_emails)

    def _check_accreditation_expiry(self, today, warning_limit, dh_users, dh_emails):
        """Check and notify about accreditation expiry."""
        contractors = self.search([])
        template_acc = self.env.ref(
            'odoo_nhs_estate_compliance.mail_template_contractor_accreditation_expiry',
            raise_if_not_found=False
        )
        template_acc_expired = self.env.ref(
            'odoo_nhs_estate_compliance.mail_template_contractor_accreditation_expired',
            raise_if_not_found=False
        )
        for contractor in contractors:
            expiring_lines = contractor.accreditation_ids.filtered(
                lambda l: l.expiry_date and l.expiry_date <= warning_limit and not l.is_expired
            )
            expired_lines = contractor.accreditation_ids.filtered(
                lambda l: l.is_expired
            )
            recipient_email = contractor.partner_id.email or dh_emails
            if expiring_lines and template_acc and recipient_email:
                template_acc.send_mail(
                    contractor.id,
                    email_values={'email_to': recipient_email},
                    force_send=True
                )
            if expired_lines and template_acc_expired and recipient_email:
                template_acc_expired.send_mail(
                    contractor.id,
                    email_values={'email_to': recipient_email},
                    force_send=True
                )
            if expiring_lines or expired_lines:
                for user in dh_users:
                    self._create_expiry_activity(
                        contractor,
                        'Accreditation',
                        min([l.expiry_date for l in expiring_lines] + [fields.Date.today() + timedelta(days=30)]),
                        dh_users
                    )
                    break

    def _create_expiry_activity(self, contractor, expiry_type, expiry_date, dh_users):
        """Create a to-do activity for Duty Holders about expiring items."""
        for user in dh_users:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.compliance.contractor'),
                ('res_id', '=', contractor.id),
                ('user_id', '=', user.id),
                ('summary', 'ilike', f'{expiry_type} Expiring'),
            ], limit=1)

            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id if activity_type else False,
                    'res_model_id': self.env['ir.model']._get_id('nhs.compliance.contractor'),
                    'res_id': contractor.id,
                    'user_id': user.id,
                    'summary': f"{expiry_type} Expiring: {contractor.name}",
                    'note': f"{expiry_type} expires on: {expiry_date}.",
                    'date_deadline': expiry_date or fields.Date.today() + timedelta(days=30),
                })

    def action_view_performance(self):
        """Open a pivot/graph/list view of all compliance tests performed by this contractor.
        Allows management to review the contractor's historical test outcomes
        and overall performance at a glance.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contractor Performance: %s' % self.name,
            'res_model': 'nhs.compliance.test',
            'view_mode': 'pivot,graph,list',
            'domain': [('contractor_id', '=', self.id)],
            'context': {
                'default_contractor_id': self.id,
            }
        }

class NHSComplianceContractorAccreditation(models.Model):
    _name = 'nhs.compliance.contractor.accreditation'
    _description = 'Contractor Accreditation'
    _order = 'name'
    _rec_name = 'code'

    name = fields.Char(
        string='Accreditation Name',
        required=True,
        help='The full name of the accreditation body or certification scheme '
             '(e.g., "National Inspection Council for Electrical Installation Contracting").'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='The standard abbreviation or code for the accreditation '
             '(e.g., "NICEIC", "Gas Safe", "LEEA"). This is used for quick identification.'
    )
    description = fields.Text(
        string='Description',
        help='A detailed description of the accreditation, including its scope, '
             'requirements, and any relevant industry standards or regulations.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive this accreditation type. Archived accreditations '
             'will not appear in dropdown selections but will be preserved for '
             'historical records.'
    )

    _uniq_code = models.Constraint(
        'unique(code)',
        'The accreditation code must be unique across the system. '
        'This code is already used by another accreditation.'
    )

class NHSContractorAccreditationLine(models.Model):
    _name = 'nhs.contractor.accreditation.line'
    _description = 'Contractor Accreditation Line'
    _order = 'expiry_date'

    contractor_id = fields.Many2one(
        'nhs.compliance.contractor',
        string='Contractor',
        required=True,
        ondelete='cascade',
        help='The contractor who holds this accreditation. When the contractor is deleted, '
             'this accreditation line will also be automatically removed.'
    )
    accreditation_id = fields.Many2one(
        'nhs.compliance.contractor.accreditation',
        string='Accreditation',
        required=True,
        ondelete='restrict',
        help='The accreditation being held by the contractor (e.g., NICEIC, Gas Safe, LEEA). '
             'This links to the master list of accreditations. The accreditation cannot be '
             'deleted if it is linked to any contractor.'
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        help='The date on which this specific contractor\'s accreditation expires. '
             'This date is used to calculate days remaining, trigger renewal notifications, '
             'and determine compliance status. Each contractor may have a different expiry '
             'date for the same accreditation.'
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_expiry_status',
        store=True,
        help='Automatically set to True when the expiry date is in the past. '
             'This flag enables quick filtering and reporting of expired accreditations '
             'that require immediate attention for renewal.'
    )
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_expiry_status',
        store=True,
        help='The number of days remaining until this accreditation expires. '
             'Positive values indicate days until expiry, negative values indicate '
             'days overdue (expired). This is used for prioritization and notifications.'
    )

    @api.onchange('expiry_date')
    def _check_expiry_date(self):
        """Ensure the expiry date is not in the past."""
        today = fields.Date.today()
        for record in self:
            if record.expiry_date :
                if record.expiry_date < today:
                    raise ValidationError(
                        "Expiry date cannot be in the past."
                    )

    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        """Compute whether the accreditation has expired and days remaining.
        Compares the expiry date against today's date to determine:
        - is_expired: True if expiry date is in the past
        - days_remaining: Positive if future, negative if expired, 0 if today
        """
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < today
                record.days_remaining = (record.expiry_date - today).days
            else:
                record.is_expired = False
                record.days_remaining = 0

    _uniq_contractor_accreditation = models.Constraint(
        'unique(contractor_id, accreditation_id)',
        'This accreditation is already assigned to this contractor. '
        'Each contractor can only have one entry per accreditation.'
    )

    _check_expiry_not_null = models.Constraint(
        'CHECK(expiry_date IS NOT NULL)',
        'The expiry date must be set for every accreditation line. '
        'Please specify when this accreditation expires.'
    )
