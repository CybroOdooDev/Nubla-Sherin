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
from odoo import fields, models


class NhsBankReportWizard(models.TransientModel):
    """Date-range (and optional area) selector driving the two board PDF
    reports: Fill-Rate & Agency-Displacement, and Bank-Spend."""
    _name = 'nhs.bank.report.wizard'
    _description = 'Staff Bank Report Wizard'

    date_from = fields.Date(string='From', required=True,
                             default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)
    org_unit_id = fields.Many2one('nhs.org.unit', string='Area / Ward (optional)')

    def _get_shifts(self):
        self.ensure_one()
        domain = [
            ('shift_start', '>=', self.date_from),
            ('shift_start', '<=', self.date_to),
        ]
        if self.org_unit_id:
            domain.append(('org_unit_id', 'child_of', self.org_unit_id.id))
        return self.env['nhs.bank.shift'].search(domain)

    def get_fill_rate_data(self):
        """Fill-rate & bank-vs-agency displacement figures for the period."""
        self.ensure_one()
        shifts = self._get_shifts()
        resolved = shifts.filtered(lambda s: s.state in ('filled', 'to_agency', 'expired'))
        filled = resolved.filtered(lambda s: s.state == 'filled')
        to_agency = resolved.filtered(lambda s: s.state == 'to_agency')
        fill_rate = (len(filled) / len(resolved) * 100.0) if resolved else 0.0
        by_area = {}
        for shift in resolved:
            key = shift.org_unit_id
            entry = by_area.setdefault(key.id, {'name': key.display_name, 'total': 0, 'filled': 0})
            entry['total'] += 1
            if shift.state == 'filled':
                entry['filled'] += 1
        area_rows = []
        for entry in by_area.values():
            entry['rate'] = round(entry['filled'] / entry['total'] * 100.0, 1) if entry['total'] else 0.0
            area_rows.append(entry)
        bank_spend = sum(self.env['nhs.shift.booking'].search([
            ('shift_id', 'in', filled.ids), ('state', 'in', ('booked', 'worked')),
        ]).mapped('payable_amount'))
        agency_spend = sum(to_agency.mapped('agency_cost'))
        comparator_pct = self.env.company.nhs_bank_agency_comparator_pct or 0.0
        return {
            'date_from': self.date_from, 'date_to': self.date_to,
            'total_resolved': len(resolved), 'filled_count': len(filled),
            'to_agency_count': len(to_agency), 'fill_rate': round(fill_rate, 1),
            'area_rows': sorted(area_rows, key=lambda r: r['name'] or ''),
            'bank_spend': bank_spend, 'agency_spend': agency_spend,
            'cost_avoidance': bank_spend * (comparator_pct / 100.0),
        }

    def get_spend_data(self):
        """Bank spend by band/rate, and agency spend, for the period."""
        self.ensure_one()
        shifts = self._get_shifts()
        bookings = self.env['nhs.shift.booking'].search([
            ('shift_id', 'in', shifts.ids), ('state', 'in', ('booked', 'worked')),
        ])
        by_band = {}
        for booking in bookings:
            band = booking.member_id.band_id
            entry = by_band.setdefault(band.id, {'name': band.name or 'Unspecified', 'hours': 0.0, 'cost': 0.0})
            if booking.shift_start and booking.shift_end:
                entry['hours'] += (booking.shift_end - booking.shift_start).total_seconds() / 3600.0
            entry['cost'] += booking.payable_amount
        agency_shifts = shifts.filtered(lambda s: s.state == 'to_agency')
        return {
            'date_from': self.date_from, 'date_to': self.date_to,
            'band_rows': sorted(by_band.values(), key=lambda r: r['name'] or ''),
            'total_bank_cost': sum(bookings.mapped('payable_amount')),
            'total_agency_cost': sum(agency_shifts.mapped('agency_cost')),
            'agency_rows': [{
                'name': s.name, 'agency': s.agency_name, 'cost': s.agency_cost,
            } for s in agency_shifts],
        }

    def action_print_fill_rate(self):
        return self.env.ref('odoo_nhs_staff_bank.action_report_nhs_fill_rate').report_action(self)

    def action_print_spend(self):
        return self.env.ref('odoo_nhs_staff_bank.action_report_nhs_bank_spend').report_action(self)
