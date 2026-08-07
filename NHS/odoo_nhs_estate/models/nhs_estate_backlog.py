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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class NHSESBacklog(models.Model):
    _name = 'nhs.estate.backlog'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Backlog Maintenance Item'
    _order = 'risk_category, name'

    name = fields.Char(
        string='Description',
        required=True,
        tracking=True,
        help="Brief description of the backlog maintenance item for quick identification"
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        required=True,
        ondelete='cascade',
        help="The building where the maintenance issue is located"
    )
    space_id = fields.Many2one(
        'nhs.estate.space',
        string='Space (optional)',
        ondelete='cascade',
        domain="[('building_id', '=', building_id)]",
        help="Specific room or space within the building where the issue exists (optional)"
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        help="Auto-generated full name combining building and space for easy reference"
    )
    element = fields.Selection([
        ('roof', 'Roof'),
        ('structure', 'Structure'),
        ('fabric', 'Fabric'),
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('fire', 'Fire'),
        ('external', 'External'),
        ('other', 'Other')
    ], string='Element Type',
        help="Building element category affected by the maintenance issue")
    risk_category = fields.Selection([
        ('high', 'High'),
        ('significant', 'Significant'),
        ('moderate', 'Moderate'),
        ('low', 'Low')
    ], string='Risk Category', required=True,
        help="Risk level assessment of the maintenance issue based on impact and urgency")
    cost_estimate = fields.Monetary(
        string='Cost Estimate',
        currency_field='currency_id',
        required=True,
        help="Estimated financial cost to rectify the maintenance issue"
    )
    target_year = fields.Integer(
        string='Target Rectification Year',
        default=lambda self: datetime.now().year,
        help="Fiscal year by which the maintenance issue is scheduled to be resolved"
    )
    status = fields.Selection([
        ('identified', 'Identified'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved')
    ], string='Status', required=True, default='identified',
        help="Current progress state of the maintenance issue resolution")
    works_ref = fields.Char(
        string='Works/Project Reference',
        help="Reference number or code linking to associated works or projects"
    )
    notes = fields.Text(string='Notes',
                    help="Additional information, observations, or special considerations about the maintenance issue")
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency used for the cost estimate (defaults to company currency)"
    )
    active = fields.Boolean(
        default=True,
        help="Indicates whether this maintenance item is active and visible"
    )

    @api.depends('building_id.name', 'space_id.name', 'name')
    def _compute_complete_name(self):
        """Compute the full hierarchical name path for this backlog item.
        Joins the building name, space name (if present), and the backlog item description
        with ' / ' delimiters.
        """
        for record in self:
            parts = []
            if record.building_id and record.building_id.name:
                parts.append(record.building_id.name)
            if record.space_id and record.space_id.name:
                parts.append(record.space_id.name)
            if record.name:
                parts.append(record.name)
            record.complete_name = ' / '.join(parts) if parts else record.name

    @api.onchange('target_year')
    def _check_target_year(self):
        """Ensure the target rectification year is not in the past.
        Raises:
            ValidationError: If target_year is older than current_year .
        """
        current_year = fields.Date.today().year
        for record in self:
            if record.target_year and record.target_year > 0 :
                if record.target_year < current_year :
                    raise ValidationError(
                        "Target rectification year cannot be years in the past."
                    )
            else :
                raise ValidationError(
                    "Provide a valid target rectification year."
                )

    @api.onchange('building_id')
    def _onchange_building_id(self):
        """Update the record's currency_id automatically when the building is changed.
        Defaults to the company currency associated with the building.
        """
        if self.building_id and self.building_id.company_id:
            self.currency_id = self.building_id.company_id.currency_id

    def _compute_display_name(self):
        """Compute the display name for each backlog record.
        Sets the display name to the full complete_name path, falling back to name.
        """
        for record in self:
            record.display_name = record.complete_name or record.name

    def write(self, vals):
        """Override write to handle target_year validation exceptions gracefully.
        Provides a user-friendly error message if target_year validation fails,
        while maintaining other changes.
        Args:
            vals (dict): Fields and values to update.
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            return super().write(vals)
        except ValidationError as e:
            if 'target_year' in vals:
                safe_vals = vals.copy()
                safe_vals.pop('target_year')
                result = super().write(safe_vals)
                raise ValidationError(
                    "The target year could not be updated. Please use a valid year (within the last 5 years)."
                ) from e
            raise

    def action_mark_planned(self):
        """Transition the backlog item's status to 'planned'."""
        self.status = 'planned'

    def action_mark_start(self):
        """Transition the backlog item's status to 'in_progress'."""
        self.status = 'in_progress'

    def action_mark_resolved(self):
        """Transition the backlog item's status to 'resolved'."""
        self.status = 'resolved'

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
            'res_id': self.building_id.id,
            'target': 'current',
        }

    def action_view_documents(self):
        """Return an action displaying all attachments/documents linked to this backlog item.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.backlog'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.backlog',
                'default_res_id': self.id,
            }
        }
    