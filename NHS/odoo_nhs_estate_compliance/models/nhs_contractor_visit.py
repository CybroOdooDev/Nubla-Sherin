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

class NHSContractorVisit(models.Model):
    """Model to manage external contractor visits, recording dates, locations, permit references, and covered items."""
    _name = 'nhs.contractor.visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contractor Visit'

    name = fields.Char(string='Visit Reference', required=True, readonly=True, copy=False, default=lambda self: 'New',
                       help='Auto-generated unique reference for this visit record.')
    contractor_id = fields.Many2one('nhs.compliance.contractor', string='Contractor', required=True,
                                    help='The external contractor who performed this site visit.')
    visit_date = fields.Date(string='Visit Date', required=True, default=fields.Date.today,
                             help='The date on which the contractor visit took place.')
    site_id = fields.Many2one('nhs.estate.site', string='Site',
                              help='The NHS estate site where the visit was conducted.')
    building_id = fields.Many2one('nhs.estate.building', string='Building',
                                  help='The specific building within the site where the visit occurred.')
    permit_ref = fields.Char(string='Permit Reference',copy=False,help='Permit-to-work reference (MGPS, HV, hot works)')
    test_ids = fields.One2many('nhs.compliance.test', 'visit_id', string='Tests Completed',
                               help='Compliance tests completed during this contractor visit.')
    item_ids = fields.Many2many('nhs.compliance.item', string='Compliance Items Covered',
                                compute='_compute_item_ids', store=True,
                                help='Compliance items that were serviced or inspected during this visit.')
    notes = fields.Text(string='Visit Summary', copy=False,
                        help='Free-text summary of work performed, observations, and any follow-up actions.')

    @api.depends('test_ids', 'test_ids.item_id')
    def _compute_item_ids(self):
        """Compute the unique compliance items covered by the tests in this contractor visit."""
        for visit in self:
            visit.item_ids = visit.test_ids.mapped('item_id')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate a visit sequence reference and synchronise schedules.
        Assigns a sequence number to new visits and updates the next_due_date
        of all linked compliance items (and their open maintenance requests) to
        match the visit date.
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('nhs.contractor.visit') or 'New'
                vals['name'] = seq
        visits = super(NHSContractorVisit, self).create(vals_list)
        for visit in visits:
            if visit.item_ids:
                visit.item_ids.write({'next_due_date': visit.visit_date})
                for item in visit.item_ids:
                    open_requests = self.env['maintenance.request'].search([
                        ('compliance_item_id', '=', item.id),
                        ('maintenance_type', '=', 'preventive'),
                        ('stage_id.done', '=', False)
                    ])
                    if open_requests:
                        open_requests.with_context(skip_maintenance_sync=True).write({
                            'schedule_date': visit.visit_date
                        })
        return visits

    def write(self, vals):
        """Override write to re-synchronise compliance item schedules when visit date or items change.
        When the visit_date or the set of linked compliance items is modified,
        updates the next_due_date on each linked compliance item and reschedules
        their open preventive maintenance requests accordingly.
        """
        res = super(NHSContractorVisit, self).write(vals)
        if 'visit_date' in vals or 'item_ids' in vals:
            for visit in self:
                if visit.item_ids:
                    visit.item_ids.write({'next_due_date': visit.visit_date})
                    for item in visit.item_ids:
                        open_requests = self.env['maintenance.request'].search([
                            ('compliance_item_id', '=', item.id),
                            ('maintenance_type', '=', 'preventive'),
                            ('stage_id.done', '=', False)
                        ])
                        if open_requests:
                            open_requests.with_context(skip_maintenance_sync=True).write({
                                'schedule_date': visit.visit_date
                            })
        return res

    def action_open_complete_wizard(self):
        """Open the wizard to complete multiple compliance items covered in this contractor visit."""
        self.ensure_one()
        contractor = self.contractor_id
        contractor_disciplines = contractor.discipline_ids if contractor else False
        domain = [('delivery_method', '=', 'contractor')]
        if contractor:
            if contractor_disciplines:
                domain.append(('discipline_id', 'in', contractor_disciplines.ids))
            domain.extend(['|', ('contractor_id', '=', False), ('contractor_id', '=', contractor.id)])
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))
        elif self.site_id:
            domain.append(('site_id', '=', self.site_id.id))
        candidate_items = self.env['nhs.compliance.item'].search(domain)
        if not candidate_items and contractor:
            fallback_domain = [('delivery_method', '=', 'contractor')]
            if contractor_disciplines:
                fallback_domain.append(('discipline_id', 'in', contractor_disciplines.ids))
            fallback_domain.extend(['|', ('contractor_id', '=', False), ('contractor_id', '=', contractor.id)])
            candidate_items = self.env['nhs.compliance.item'].search(fallback_domain)
        wizard = self.env['nhs.contractor.visit.complete.wizard'].create({
            'visit_id': self.id,
            'common_outcome': 'pass',
            'common_certificate_date': fields.Date.today(),
            'common_issuing_body': contractor.name if contractor else False,
        })
        line_vals = []
        for item in candidate_items:
            line_vals.append({
                'wizard_id': wizard.id,
                'item_id': item.id,
                'selected': True,
                'outcome': 'pass',
                'certificate_date': fields.Date.today(),
                'issuing_body': contractor.name if contractor else False,
            })
        if line_vals:
            self.env['nhs.contractor.visit.complete.wizard.line'].create(line_vals)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Complete Multiple Compliance Items',
            'res_model': 'nhs.contractor.visit.complete.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
