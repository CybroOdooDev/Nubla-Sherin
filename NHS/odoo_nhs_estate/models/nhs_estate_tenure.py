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
import logging
from datetime import timedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class NHSESTenure(models.Model):
    _name = 'nhs.estate.tenure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tenure & Lease Detail'
    _order = 'name'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        required=True,
        help="Auto-generated name combining building and tenure type for easy identification"
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        required=True,
        ondelete='restrict',
        domain="[('operational_status', 'in', ['operational','partial'])]",
        help="The building to which this tenure record applies"
    )
    tenure_type = fields.Selection([
        ('freehold', 'Freehold'),
        ('leasehold', 'Leasehold'),
        ('pfi', 'PFI'),
        ('lift', 'LIFT'),
        ('nhsps', 'NHSPS'),
        ('chp', 'CHP'),
        ('licence', 'Licence')
    ], string='Tenure Type',
        required=True,
        help="Type of tenure or property arrangement for the building (e.g., Freehold, Leasehold, PFI, LIFT)"
    )
    landlord = fields.Char(
        string='Landlord/NHSPS/CHP Name',
        help="Name of the landlord, NHSPS (NHS Property Services), or CHP (Community Health Partnerships) entity"
    )
    lease_start = fields.Date(
        string='Lease Start Date',
        help="Date when the lease or tenure agreement commenced"
    )
    lease_end = fields.Date(
        string='Lease End Date',
        help="Date when the lease or tenure agreement expires"
    )
    lease_term_years = fields.Integer(
        string='Lease Term (years)',
        compute='_compute_lease_term',
        help="Total duration of the lease in years (auto-calculated from start and end dates)"
    )
    break_date = fields.Date(
        string='Break Clause Date',
        help="Date when a break clause can be exercised to terminate the lease early"
    )
    rent_amount = fields.Monetary(
        string='Annual Rent/Unitary Charge',
        currency_field='currency_id',
        help="Annual rent amount payable or unitary charge for PFI/LIFT arrangements"
    )
    rent_review_date = fields.Date(
        string='Rent Review Date',
        help="Date when the next rent review is scheduled"
    )
    contract_ref = fields.Char(
        string='PFI/LIFT Contract or Occupancy Ref',
        help="Reference number for PFI/LIFT contracts or occupancy agreements"
    )
    contract_start = fields.Date(
        string='Contract Start Date',
        help="Start date of the PFI/LIFT contract or occupancy agreement"
    )
    contract_end = fields.Date(
        string='Contract End Date',
        help="End date of the PFI/LIFT contract or occupancy agreement"
    )
    document_ids = fields.Many2many(
        'ir.attachment',
        string='Lease/Contract Documents',
        help="Supporting documents including lease agreements, contracts, and related legal documents"
    )
    expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_expiring_soon',
        store=True,
        help="Indicates whether the lease/contract is approaching its expiry date (auto-calculated)"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency used for rent and financial values (defaults to company currency)"
    )

    @api.model
    def default_get(self, fields_list):
        """Set default name for new records."""
        defaults = super().default_get(fields_list)
        if 'name' in fields_list and not defaults.get('name'):
            defaults['name'] = 'New Tenure'
        return defaults

    @api.depends('tenure_type', 'building_id.name')
    def _compute_name(self):
        """Compute a descriptive name for this tenure record.
        Combines the string label of the tenure_type selection and the building name
        (e.g., 'Leasehold — Building A').
        """
        for record in self:
            tenure_label = dict(self._fields['tenure_type'].selection).get(record.tenure_type, '')
            building_name = record.building_id.name or ''
            record.name = f"{tenure_label} — {building_name}"

    @api.depends('lease_start', 'lease_end')
    def _compute_lease_term(self):
        """Calculate the total lease duration term in years.
        Computes the fractional years between lease_start and lease_end dates.
        """
        for record in self:
            if record.lease_start and record.lease_end:
                delta = record.lease_end - record.lease_start
                record.lease_term_years = delta.days / 365.25
            else:
                record.lease_term_years = 0

    @api.depends('lease_end', 'break_date', 'contract_end')
    def _compute_expiring_soon(self):
        """Check if any key lease or contract dates are within the 12-month expiry threshold.
        Sets expiring_soon to True if lease_end, break_date, or contract_end falls
        within 365 days of the current date.
        """
        for record in self:
            expiring = False
            today = fields.Date.today()
            threshold = today + timedelta(days=365)
            if record.lease_end and record.lease_end <= threshold:
                expiring = True
            if record.break_date and record.break_date <= threshold:
                expiring = True
            if record.contract_end and record.contract_end <= threshold:
                expiring = True
            record.expiring_soon = expiring

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to construct and assign the record name before validation.
        Args:
            vals_list (list of dicts): Field values for new records.
        Returns:
            recordset: Newly created tenure records.
        """
        for vals in vals_list:
            if 'name' not in vals or not vals.get('name'):
                if 'building_id' in vals and 'tenure_type' in vals:
                    building = self.env['nhs.estate.building'].browse(vals['building_id'])
                    tenure_label = dict(self._fields['tenure_type'].selection).get(vals['tenure_type'], '')
                    if building:
                        vals['name'] = f"{tenure_label} — {building.name}"
                    else:
                        vals['name'] = f"New {tenure_label}"
                else:
                    vals['name'] = 'New Tenure'
        return super().create(vals_list)

    def write(self, vals):
        """Override write to update the record name if building or tenure type changes.
        Args:
            vals (dict): Fields and values to update.
        Returns:
            bool: True if successful, False otherwise.
        """
        if 'building_id' in vals or 'tenure_type' in vals:
            for record in self:
                # Get the new values or keep existing
                building_id = vals.get('building_id', record.building_id.id)
                tenure_type = vals.get('tenure_type', record.tenure_type)
                if building_id and tenure_type:
                    building = self.env['nhs.estate.building'].browse(building_id)
                    tenure_label = dict(self._fields['tenure_type'].selection).get(tenure_type, '')
                    # Only update name if it's not explicitly set in vals
                    if 'name' not in vals or not vals.get('name'):
                        vals['name'] = f"{tenure_label} — {building.name}"
        return super().write(vals)

    def action_view_building(self):
        """Return an action displaying the detail form view of the associated building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Building',
            'res_model': 'nhs.estate.building',
            'view_mode': 'form',
            'res_id': self.building_id.id
        }

    def action_view_documents(self):
        """Return an action showing all documents and attachments linked to this tenure.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.tenure'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.tenure',
                'default_res_id': self.id,
            }
        }

    def _create_break_clause_activity(self, tenure):
        """Create a mail activity reminder for an upcoming break clause date.
        Generates a warning task assigned to the record creator or current user
        scheduled 10 days prior to the break clause date, avoiding duplicates.
        Args:
            tenure (recordset): A single nhs.estate.tenure record.
        Returns:
            bool: True if activity created successfully, False otherwise.
        """
        try:
            existing_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.estate.tenure'),
                ('res_id', '=', tenure.id),
                ('note', 'ilike', 'Break Clause Reminder'),
                ('date_deadline', '=', tenure.break_date - timedelta(days=10))
            ], limit=1)
            if existing_activity:
                return False
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([], limit=1)
            if not activity_type:
                return False
            activity_vals = {
                'res_model_id': self.env['ir.model']._get_id('nhs.estate.tenure'),
                'res_id': tenure.id,
                'activity_type_id': activity_type.id,
                'summary': f' Break Clause Review: {tenure.name}',
                'note': f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h3>Break Clause Reminder</h3>
                        <table style="border-collapse: collapse; width: 100%;">
                            <tr><td style="padding: 5px;"><strong>Building:</strong></td>
                                <td style="padding: 5px;">{tenure.building_id.name}</td></tr>
                            <tr><td style="padding: 5px;"><strong>Break Date:</strong></td>
                                <td style="padding: 5px; color: red;">{tenure.break_date.strftime('%d/%m/%Y')}</td></tr>
                            <tr><td style="padding: 5px;"><strong>Days until break:</strong></td>
                                <td style="padding: 5px;">{(tenure.break_date - fields.Date.today()).days} days</td></tr>
                        </table>
                        <p style="margin-top: 10px;"><strong>Action Required:</strong> Review break clause options and 
                        prepare for potential lease termination or renegotiation.</p>
                    </div>
                """,
                'date_deadline': tenure.break_date - timedelta(days=10),
                'user_id': tenure.create_uid.id or self.env.user.id,
            }
            self.env['mail.activity'].create(activity_vals)
            tenure.message_post(
                body=f"Break clause reminder activity created for {tenure.break_date.strftime('%d/%m/%Y')}",
                message_type='comment'
            )
            return True
        except Exception as e:
            _logger.exception("Failed to create break clause activity for tenure %s: %s", tenure.id, e)
            return False

    def _create_rent_review_activity(self, tenure):
        """Create a mail activity reminder for an upcoming rent review date.
        Generates a task assigned to the record creator or current user
        scheduled 10 days prior to the rent review date, avoiding duplicates.
        Args:
            tenure (recordset): A single nhs.estate.tenure record.
        Returns:
            bool: True if activity created successfully, False otherwise.
        """
        try:
            existing_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.estate.tenure'),
                ('res_id', '=', tenure.id),
                ('note', 'ilike', 'Rent Review Reminder'),
                ('date_deadline', '=', tenure.rent_review_date - timedelta(days=10))
            ], limit=1)
            if existing_activity:
                return False
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([], limit=1)
            if not activity_type:
                return False
            activity_vals = {
                'res_model_id': self.env['ir.model']._get_id('nhs.estate.tenure'),
                'res_id': tenure.id,
                'activity_type_id': activity_type.id,
                'summary': f' Rent Review: {tenure.name}',
                'note': f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h3>Rent Review Reminder</h3>
                        <table style="border-collapse: collapse; width: 100%;">
                            <tr><td style="padding: 5px;"><strong>Building:</strong></td>
                                <td style="padding: 5px;">{tenure.building_id.name}</td></tr>
                            <tr><td style="padding: 5px;"><strong>Review Date:</strong></td>
                                <td style="padding: 5px; color: orange;">{tenure.rent_review_date.strftime('%d/%m/%Y')}
                                </td></tr>
                        </table>
                        <p style="margin-top: 10px;"><strong>Action Required:</strong> Prepare for rent review. 
                        Gather market data, review terms, and negotiate new rent amount.</p>
                    </div>
                """,
                'date_deadline': tenure.rent_review_date - timedelta(days=10),
                'user_id': tenure.create_uid.id or self.env.user.id,
            }
            self.env['mail.activity'].create(activity_vals)
            tenure.message_post(
                body=f" Rent review reminder activity created for {tenure.rent_review_date.strftime('%d/%m/%Y')}",
                message_type='comment'
            )
            return True
        except Exception as e:
            _logger.exception("Failed to create rent review activity for tenure %s: %s", tenure.id, e)
            return False

    @api.model
    def cron_create_break_clause_reminders(self):
        """Cron job to automatically create break clause reminders for leases expiring within 15-30 days.
        Searches for active tenure records with break clause dates in the upcoming
        15-30 day window and triggers creation of reminder mail activities.
        Returns:
            bool: True upon successful execution of the batch activity creation.
        """
        today = fields.Date.today()
        start_date = today + timedelta(days=15)
        end_date = today + timedelta(days=30)
        tenures = self.search([
            ('break_date', '!=', False),
            ('break_date', '>=', start_date),
            ('break_date', '<=', end_date)
        ])
        for tenure in tenures:
            self._create_break_clause_activity(tenure)
        return True

    @api.model
    def cron_create_rent_review_reminders(self):
        """Cron job to automatically create rent review reminders for leases reviewing within 15-30 days.
        Searches for active tenure records with rent review dates in the upcoming
        15-30 day window and triggers creation of rent review mail activities.
        Returns:
            bool: True upon successful execution of the batch activity creation.
        """
        today = fields.Date.today()
        start_date = today + timedelta(days=15)
        end_date = today + timedelta(days=30)
        tenures = self.search([
            ('rent_review_date', '!=', False),
            ('rent_review_date', '>=', start_date),
            ('rent_review_date', '<=', end_date)
        ])
        for tenure in tenures:
            self._create_rent_review_activity(tenure)
        return True
