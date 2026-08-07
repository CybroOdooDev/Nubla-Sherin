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

class NHSComplianceDiscipline(models.Model):
    """Model representing statutory compliance disciplines such as Fire, Water, Electrical, etc."""
    _name = 'nhs.compliance.discipline'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Statutory compliance discipline (water, fire, electrical, …)'
    _order = 'sequence, name'

    name = fields.Char(string='Discipline Name', required=True,
                       help='The name of the statutory compliance discipline (e.g. Water, Fire, Electrical).')
    code = fields.Char(string='Code', required=True, index=True,
                       help='A unique short code identifying the discipline (e.g. WAT, FIRE, ELEC).')
    htm_reference = fields.Char(string='HTM Reference', help='Primary HTM reference (e.g. HTM 04-01, HTM 05, HTM 06)')
    legislation_reference = fields.Char(string='Legislation Reference',
                                        help='Primary regulation (e.g. COSHH / ACOP L8, RRO 2005, LOLER 1998)')
    description = fields.Text(string='Description', help='What the discipline covers')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Determines the display order of disciplines; lower values appear first.')
    active = fields.Boolean(string='Active', default=True, help='Enable/disable per organisation')
    lead_days = fields.Integer(string='Lead Days', default=14, help='Amber window in days for this discipline')
    type_ids = fields.One2many('nhs.compliance.type', 'discipline_id',string='Compliance Types',
                               help='The compliance test types that belong to this discipline.')
    item_count = fields.Integer(string='Live Items', compute='_compute_item_count',
                                help='Total number of active compliance items across all types in this discipline.')
    contractor_count = fields.Integer(string='Contractors Count', compute='_compute_contractor_count',
                                      help='Number of contractors registered to work within this discipline.')

    _sql_constraints_code_unique = models.Constraint(
        'unique(code)',
        'Discipline code must be unique.'
    )

    @api.depends('type_ids.item_count')
    def _compute_item_count(self):
        """Compute the total number of active compliance items across all types in this discipline."""
        for discipline in self:
            discipline.item_count = sum(discipline.type_ids.mapped('item_count'))

    def _compute_contractor_count(self):
        """Compute the number of contractors associated with this discipline."""
        for discipline in self:
            discipline.contractor_count = self.env['nhs.compliance.contractor'].search_count([
                ('discipline_ids', 'in', discipline.id)
            ])

    @api.constrains('code')
    def _check_code_unique(self):
        """Validate that the discipline code is unique across all records."""
        existing = self.search([('code', '=', self.code), ('id', '!=', self.id)])
        if existing:
            raise ValidationError('Code must be unique')

    def action_view_compliance_item(self):
        """Open a list/form view of all compliance items belonging to this discipline."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Spaces',
            'res_model': 'nhs.compliance.item',
            'view_mode': 'list,form',
            'domain': [('discipline_id', '=', self.id)],
            'context': {'default_discipline_id': self.id}
        }

    def action_view_contractors(self):
        """Open a list/form view of all contractors registered for this discipline."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contractors',
            'res_model': 'nhs.compliance.contractor',
            'view_mode': 'list,form',
            'domain': [('discipline_ids', 'in', self.id)],
            'context': {'default_discipline_ids': [(4, self.id)]}
        }
