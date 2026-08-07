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
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import NhsComplaintCommon


@tagged('post_install', '-at_install')
class TestConstraints(NhsComplaintCommon):
    """@api.constrains validation across the module's models."""

    def test_received_at_cannot_be_future(self):
        """received_at is a factual intake timestamp — the future is invalid."""
        with self.assertRaises(ValidationError):
            self._new_pals(received_at=fields.Datetime.now() + timedelta(days=2))

    def test_third_party_consent_required(self):
        """A third-party complaint must not keep consent status 'not_required'."""
        with self.assertRaises(ValidationError):
            self._new_complaint(is_third_party=True, consent_status='not_required')
        # An explicit consent status is accepted.
        rec = self._new_complaint(is_third_party=True, consent_status='pending')
        self.assertEqual(rec.consent_status, 'pending')

    def test_vexatious_note_required(self):
        """Flagging a complainant vexatious requires a documented handling note."""
        with self.assertRaises(ValidationError):
            self.Complainant.create({
                'name': 'Habitual Complainer',
                'relationship_to_patient': 'self',
                'is_vexatious': True,
            })
        # With the note it is allowed.
        rec = self.Complainant.create({
            'name': 'Habitual Complainer',
            'relationship_to_patient': 'self',
            'is_vexatious': True,
            'vexatious_note': 'Agreed single point of contact.',
        })
        self.assertTrue(rec.is_vexatious)

    def test_subject_two_level_limit(self):
        """The KO41a subject taxonomy is capped at two levels."""
        # subject_child already has a parent, so nesting a third level is invalid.
        with self.assertRaises(ValidationError):
            self.Subject.create({
                'name': 'Third level',
                'parent_id': self.subject_child.id,
            })

    def test_phso_outcome_blocked_before_decision(self):
        """Outcome/compensation/recommendations may not be set while referred."""
        complaint = self._new_complaint()
        complaint.action_escalate_phso()
        phso = complaint.phso_id
        self.assertEqual(phso.state, 'referred')
        with self.assertRaises(ValidationError):
            phso.write({'outcome': 'upheld'})
        # Once a decision is made, the outcome can be recorded.
        phso.action_mark_under_review()
        phso.action_record_decision()
        phso.write({'outcome': 'upheld', 'recommendations': 'Apologise.'})
        self.assertEqual(phso.outcome, 'upheld')

    def test_correspondence_cannot_be_deleted(self):
        """Correspondence log entries are statutory and cannot be unlinked."""
        complaint = self._new_complaint()
        corr = self.Correspondence.create({
            'complaint_id': complaint.id,
            'direction': 'inbound',
            'channel': 'email',
            'summary': 'Complainant chased for an update.',
        })
        with self.assertRaises(UserError):
            corr.unlink()

    def test_phso_cannot_be_deleted(self):
        """PHSO escalation records are statutory and cannot be unlinked."""
        complaint = self._new_complaint()
        complaint.action_escalate_phso()
        with self.assertRaises(UserError):
            complaint.phso_id.unlink()

    def test_action_single_parent(self):
        """An action may be linked to only one parent source record."""
        complaint = self._new_complaint()
        incident = self._make_incident()
        with self.assertRaises(ValidationError):
            self.env['nhs.action'].create({
                'name': 'Ambiguous action',
                'due_date': fields.Date.today(),
                'complaint_id': complaint.id,
                'incident_id': incident.id,
            })

    def test_action_blocked_on_closed_complaint(self):
        """Actions cannot be created against a resolved/closed complaint."""
        pals = self._new_pals()
        pals.action_pals_in_progress()
        pals.action_pals_resolve()  # -> resolved
        with self.assertRaises(ValidationError):
            self.env['nhs.action'].create({
                'name': 'Too late',
                'due_date': fields.Date.today(),
                'complaint_id': pals.id,
            })

    def test_action_links_to_complaint_investigation(self):
        """An action linked via complaint_investigation_id appears on the
        investigation's action_ids (dedicated inverse, not the incident one)."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        complaint.action_start_investigation()
        inv = complaint.investigation_id
        action = self.env['nhs.action'].create({
            'name': 'Retrain triage nurses',
            'due_date': fields.Date.today(),
            'complaint_investigation_id': inv.id,
        })
        self.assertIn(action, inv.action_ids)

    def test_action_blocked_on_completed_investigation(self):
        """Actions cannot be created against a completed complaint investigation."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        complaint.action_start_investigation()
        inv = complaint.investigation_id
        inv.action_complete()
        with self.assertRaises(ValidationError):
            self.env['nhs.action'].create({
                'name': 'Too late',
                'due_date': fields.Date.today(),
                'complaint_investigation_id': inv.id,
            })

    # ── helper ────────────────────────────────────────────────────────────
    def _make_incident(self):
        """Create a minimal nhs.incident record for use as an alternate action parent."""
        location = self.env['nhs.location'].create({'name': 'Ward A'})
        category = self.env['nhs.incident.category'].create({'name': 'Falls'})
        return self.env['nhs.incident'].create({
            'incident_kind': 'incident',
            'occurred_at': fields.Datetime.now() - timedelta(days=1),
            'reported_at': fields.Datetime.now(),
            'description': 'Patient fall.',
            'location_id': location.id,
            'category_id': category.id,
            'harm_grade': 'no_harm',
        })
