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
from odoo import api, models, fields

class ReportComplianceBoard(models.AbstractModel):
    """QWeb PDF report parser for rendering the Compliance Board Assurance report."""
    _name = 'report.odoo_nhs_estate_compliance.report_nhs_board_view'
    _description = 'Compliance Board Assurance QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the Board Assurance compliance PDF report.
        Calculates point-in-time compliance statistics (overall, by discipline,
        by site), identifies key risks (failed or high-criticality overdue items),
        and returns all aggregated data for the QWeb report template.  Filters
        records by the 'As At Date' from context to support historical reporting.
        """
        if not docids:
            docids = self.env['nhs.compliance.item'].search([('active', '=', True)]).ids
        docs = self.env['nhs.compliance.item'].browse(docids)
        as_at_date = self.env.context.get('till_date') or fields.Date.today()
        if isinstance(as_at_date, str):
            as_at_date = fields.Date.to_date(as_at_date)
        # Filter docs created on or before as_at_date
        docs = docs.filtered(lambda i: i.create_date.date() <= as_at_date)
        total_items = len(docs)
        item_statuses = {i.id: i.get_status_as_of(as_at_date) for i in docs}
        compliant_count = sum(1 for i in docs if item_statuses[i.id] == 'compliant')
        due_soon_count = sum(1 for i in docs if item_statuses[i.id] == 'due_soon')
        overdue_count = sum(1 for i in docs if item_statuses[i.id] == 'overdue')
        failed_count = sum(1 for i in docs if item_statuses[i.id] == 'failed')
        compliance_rate = (compliant_count / total_items * 100.0) if total_items else 100.0
        disciplines = docs.mapped('discipline_id')
        discipline_stats = []
        for d in disciplines:
            d_items = docs.filtered(lambda i: i.discipline_id == d)
            d_total = len(d_items)
            d_compliant = sum(1 for i in d_items if item_statuses[i.id] == 'compliant')
            d_rate = (d_compliant / d_total * 100.0) if d_total else 0.0
            discipline_stats.append({
                'name': d.name,
                'htm': d.htm_reference or 'N/A',
                'total': d_total,
                'compliant': d_compliant,
                'rate': round(d_rate, 1),
            })
        sites = docs.mapped('site_id')
        site_stats = []
        for s in sites:
            s_items = docs.filtered(lambda i: i.site_id == s)
            s_total = len(s_items)
            s_compliant = sum(1 for i in s_items if item_statuses[i.id] == 'compliant')
            s_rate = (s_compliant / s_total * 100.0) if s_total else 0.0
            site_stats.append({
                'name': s.name,
                'total': s_total,
                'compliant': s_compliant,
                'rate': round(s_rate, 1),
            })
        key_risks = docs.filtered(
            lambda i: item_statuses[i.id] == 'failed' or (item_statuses[i.id] == 'overdue' and
                                                          i.compliance_type_id.criticality in ['life_safety', 'high'])
        )
        overdue_items = docs.filtered(lambda i: item_statuses[i.id] == 'overdue')
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.compliance.item',
            'docs': docs,
            'site_name': data.get('site_name') if data else 'Whole Estate',
            'total_items': total_items,
            'compliant_count': compliant_count,
            'due_soon_count': due_soon_count,
            'overdue_count': overdue_count,
            'failed_count': failed_count,
            'compliance_rate': round(compliance_rate, 1),
            'discipline_stats': discipline_stats,
            'site_stats': site_stats,
            'key_risks': key_risks,
            'overdue_items': overdue_items,
            'item_statuses': item_statuses,
            'as_at_date': as_at_date,
        }
