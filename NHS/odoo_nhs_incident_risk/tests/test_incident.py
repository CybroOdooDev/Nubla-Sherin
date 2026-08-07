# -*- coding: utf-8 -*-
"""Incident model: sequencing, state-machine guard, workflow actions, harm
rules / Duty-of-Candour auto-creation, constraints, and the triage wizard."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestIncident(NhsCommon):

    def test_create_assigns_sequence_reference(self):
        """A new incident gets an auto INC/ reference, not the placeholder 'New'."""
        inc = self._make_incident()
        self.assertNotEqual(inc.name, 'New')
        self.assertTrue(inc.name.startswith('INC/'))

    def test_occurred_at_future_rejected(self):
        """occurred_at in the future violates the @api.constrains guard."""
        with self.assertRaises(ValidationError):
            self._make_incident(occurred_at=fields.Datetime.now() + timedelta(days=1))

    def test_state_cannot_be_written_directly(self):
        """state is workflow-controlled: a plain write must raise UserError."""
        inc = self._make_incident()
        with self.assertRaises(UserError):
            inc.write({'state': 'triage'})

    def test_action_accept_moves_to_triage(self):
        """action_accept transitions a New incident to Triage via the guarded path."""
        inc = self._make_incident()
        inc.action_accept()
        self.assertEqual(inc.state, 'triage')

    def test_moderate_harm_autocreates_duty_of_candour(self):
        """Harm >= company trigger grade auto-creates a linked DoC record."""
        inc = self._make_incident(harm_grade='moderate')
        self.assertTrue(inc.doc_id, 'DoC should be auto-created at moderate harm')
        self.assertEqual(inc.doc_id.incident_id, inc)

    def test_low_harm_does_not_create_duty_of_candour(self):
        """Harm below the trigger grade must NOT create a DoC obligation."""
        inc = self._make_incident(harm_grade='low')
        self.assertFalse(inc.doc_id)

    def test_never_event_forces_psii(self):
        """Flagging a Never Event forces the PSIRF response level to PSII."""
        inc = self._make_incident(is_never_event=True)
        self.assertEqual(inc.response_level, 'psii')

    def test_rejected_requires_reason(self):
        """Moving to 'rejected' with no rejection_reason violates the constraint."""
        inc = self._make_incident()
        with self.assertRaises(ValidationError):
            inc.with_context(nhs_workflow=True).write({'state': 'rejected'})

    def test_duplicate_requires_master(self):
        """Marking 'duplicate' without a master incident violates the constraint."""
        inc = self._make_incident()
        with self.assertRaises(ValidationError):
            inc.with_context(nhs_workflow=True).write({'state': 'duplicate'})

    def test_start_investigation_requires_triage_and_grading(self):
        """start_investigation guards: must be triaged and graded first."""
        inc = self._make_incident()
        with self.assertRaises(UserError):
            inc.action_start_investigation()  # still 'new'
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({
            'harm_grade': 'moderate', 'response_level': 'psii'})
        inc.action_start_investigation()
        self.assertEqual(inc.state, 'investigation')
        self.assertTrue(inc.investigation_id)
        self.assertEqual(inc.investigation_id.response_level, 'psii')

    def test_start_investigation_none_response_skips_to_actions(self):
        """A 'none' response level skips investigation and goes straight to Actions."""
        inc = self._make_incident()
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({
            'harm_grade': 'low', 'response_level': 'none'})
        inc.action_start_investigation()
        self.assertEqual(inc.state, 'actions')
        self.assertFalse(inc.investigation_id)

    def test_request_closure_blocked_by_open_action(self):
        """Closure cannot be requested while an action is still open."""
        inc = self._make_incident()
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({'state': 'actions'})
        self.env['nhs.action'].create({
            'name': 'Fix the floor', 'incident_id': inc.id,
            'owner_id': self.env.user.id,
            'due_date': fields.Date.today() + timedelta(days=7),
        })
        with self.assertRaises(UserError):
            inc.action_request_closure()

    def test_close_requires_quality_lead(self):
        """Only Quality Lead users may close an incident."""
        inc = self._make_incident()
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({'state': 'pending_closure'})
        # Handler is not a quality lead -> blocked.
        with self.assertRaises(UserError):
            inc.with_user(self.user_handler).action_close()
        # Quality lead succeeds and stamps closed_at.
        inc.with_user(self.user_quality).action_close()
        self.assertEqual(inc.state, 'closed')
        self.assertTrue(inc.closed_at)

    def test_counts_compute(self):
        """Smart-button counts reflect linked persons/actions."""
        inc = self._make_incident()
        self.env['nhs.incident.person'].create({
            'incident_id': inc.id, 'person_type': 'patient', 'harm_observed': 'low'})
        self.env['nhs.action'].create({
            'name': 'A', 'incident_id': inc.id, 'owner_id': self.env.user.id,
            'due_date': fields.Date.today()})
        self.assertEqual(inc.person_count, 1)
        self.assertEqual(inc.action_count, 1)

    def test_triage_wizard_accept_path(self):
        """Triage wizard (accept) writes grading back and moves incident to Triage."""
        inc = self._make_incident()
        wiz = self.env['nhs.triage.wizard'].create({
            'incident_id': inc.id,
            'category_id': self.inc_cat.id,
            'location_id': self.location.id,
            'harm_grade': 'moderate',
            'response_level': 'aar',
            'decision': 'accept',
            'handler_id': self.user_handler.id,
        })
        wiz.action_confirm()
        self.assertEqual(inc.state, 'triage')
        self.assertEqual(inc.harm_grade, 'moderate')
        self.assertEqual(inc.handler_id, self.user_handler)

    def test_triage_wizard_reject_requires_reason(self):
        """Triage wizard reject path requires a rejection reason."""
        inc = self._make_incident()
        wiz = self.env['nhs.triage.wizard'].create({
            'incident_id': inc.id, 'category_id': self.inc_cat.id,
            'location_id': self.location.id, 'harm_grade': 'no_harm',
            'response_level': 'none', 'decision': 'reject',
        })
        with self.assertRaises(UserError):
            wiz.action_confirm()

    def test_days_to_close_excludes_weekends(self):
        """days_to_close counts working days only (Mon report -> next Mon close = 5)."""
        inc = self._make_incident()
        # Use a clean working-day window with no seeded bank holidays nearby.
        self.env['nhs.holiday'].search([]).unlink()
        inc.reported_at = fields.Datetime.to_datetime('2026-06-01 09:00:00')  # Monday
        inc.with_context(nhs_workflow=True).write(
            {'closed_at': fields.Datetime.to_datetime('2026-06-08 09:00:00')})  # next Monday
        self.assertEqual(inc.days_to_close, 5)
