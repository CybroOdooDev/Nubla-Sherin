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
from datetime import date, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import Form, tagged

from .common import NhsComplaintCommon


@tagged('post_install', '-at_install')
class TestComputedFields(NhsComplaintCommon):
    """Computed / related fields and their @api.depends triggers."""

    def test_within_time_limit_true_when_recent(self):
        """An event within 12 months of receipt is inside the time limit."""
        rec = self._new_complaint(
            event_date=date.today() - timedelta(days=30),
            received_at=fields.Datetime.now(),
        )
        self.assertTrue(rec.within_time_limit)

    def test_within_time_limit_false_when_stale(self):
        """An event more than 12 months before receipt falls outside the limit."""
        rec = self._new_complaint(
            event_date=date.today() - timedelta(days=800),
            received_at=fields.Datetime.now(),
        )
        self.assertFalse(rec.within_time_limit)

    @freeze_time('2026-06-15 12:00:00')  # a Monday (noon avoids "future" intake)
    def test_ack_deadline_working_days(self):
        """Formal complaint ack deadline = received_at + 3 working days (skips weekend)."""
        rec = self._new_complaint(received_at='2026-06-15 09:00:00')
        # Mon 15th + 3 working days -> Thu 18th June 2026.
        self.assertEqual(rec.ack_deadline, date(2026, 6, 18))

    @freeze_time('2026-06-15 12:00:00')
    def test_ack_deadline_none_for_pals(self):
        """PALS concerns have no statutory acknowledgement deadline."""
        rec = self._new_pals(received_at='2026-06-15 09:00:00')
        self.assertFalse(rec.ack_deadline)

    def test_days_to_respond(self):
        """days_to_respond counts working days between receipt and response sent."""
        rec = self._new_complaint(received_at='2026-06-15 09:00:00')
        rec.write({'response_sent_at': '2026-06-19 15:00:00'})  # Mon -> Fri
        self.assertEqual(rec.days_to_respond, 4)

    def test_overdue_flags(self):
        """ack_overdue / response_overdue flip when deadlines pass and work is open."""
        rec = self._new_complaint(
            received_at=self._days_ago(30),
            response_deadline=date.today() - timedelta(days=1),
        )
        self.assertTrue(rec.ack_overdue,
                        'Unacknowledged complaint past its ack deadline is overdue.')
        self.assertTrue(rec.response_overdue,
                        'Open complaint past its response deadline is overdue.')

    def test_counts(self):
        """Smart-button counters reflect the linked records."""
        complaint = self._new_complaint()
        self.Correspondence.create({
            'complaint_id': complaint.id,
            'direction': 'inbound',
            'channel': 'email',
            'summary': 'Initial email.',
        })
        self.assertEqual(complaint.correspondence_count, 1)
        self.assertEqual(complaint.incident_count, 0)
        self.assertEqual(complaint.action_count, 0)

    def test_complainant_count(self):
        """nhs.complainant.complaint_count reflects its linked complaints."""
        complainant = self.Complainant.create({
            'name': 'Repeat Complainant',
            'relationship_to_patient': 'self',
        })
        self._new_complaint(complainant_id=complainant.id)
        self._new_complaint(complainant_id=complainant.id)
        self.assertEqual(complainant.complaint_count, 2)

    def test_subject_complete_name(self):
        """Two-level subject builds a 'Parent / Child' complete name."""
        self.assertEqual(
            self.subject_child.complete_name,
            f'{self.subject_parent.name} / {self.subject_child.name}',
        )

    def test_onchange_complainant_populates_inline_fields(self):
        """Selecting a complainant copies its details onto the complaint (Form)."""
        complainant = self.Complainant.create({
            'name': 'Jordan Carer',
            'email': 'jordan@carer.test',
            'phone': '0100 000000',
            'relationship_to_patient': 'carer',
        })
        form = Form(self.Complaint)
        form.subject_summary = 'Test'
        form.description = 'Test narrative'
        form.subject_id = self.subject_child
        form.complainant_id = complainant
        self.assertEqual(form.complainant_name, 'Jordan Carer')
        self.assertEqual(form.complainant_email, 'jordan@carer.test')
        self.assertEqual(form.complainant_relationship, 'carer')

    def test_onchange_multi_org_defaults_lead_org(self):
        """Ticking Multi-Organisation defaults the lead org to the current company."""
        form = Form(self.Complaint)
        form.subject_summary = 'Joint'
        form.description = 'Spans two trusts'
        form.subject_id = self.subject_child
        form.is_multi_org = True
        self.assertEqual(form.lead_org_id, self.company.partner_id)
