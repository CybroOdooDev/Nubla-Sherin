# -*- coding: utf-8 -*-
"""CAPA actions (single-parent rule, evidence/verify workflow) and the
PSIRF investigation lifecycle (submit/approve gating, incident advancement)."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestAction(NhsCommon):

    def _action(self, **overrides):
        vals = {
            'name': 'Update SOP', 'owner_id': self.env.user.id,
            'due_date': fields.Date.today() + timedelta(days=7),
        }
        vals.update(overrides)
        return self.env['nhs.action'].create(vals)

    def test_reference_sequence(self):
        """A new action receives an auto ACT/ reference."""
        act = self._action()
        self.assertTrue(act.reference.startswith('ACT/'))

    def test_single_parent_constraint(self):
        """An action linked to two unrelated parents violates the constraint."""
        inc = self._make_incident()
        risk = self._make_risk()
        with self.assertRaises(ValidationError):
            self._action(incident_id=inc.id, risk_id=risk.id)

    def test_evidence_required_before_review(self):
        """Submitting for evidence review requires completion evidence."""
        act = self._action()
        act.action_start()
        with self.assertRaises(UserError):
            act.action_submit_evidence()
        act.completion_evidence = 'SOP v2 published and circulated.'
        act.action_submit_evidence()
        self.assertEqual(act.state, 'evidence_review')

    def test_verify_sets_done_and_verifier(self):
        """Verifying an action records the verifier and timestamp."""
        act = self._action(completion_evidence='done')
        act.action_verify()
        self.assertEqual(act.state, 'done')
        self.assertEqual(act.verified_by_id, self.env.user)
        self.assertTrue(act.verified_at)

    def test_write_guard_blocks_review_without_evidence(self):
        """A direct write to evidence_review without evidence is blocked."""
        act = self._action()
        with self.assertRaises(UserError):
            act.write({'state': 'evidence_review'})


@tagged('post_install', '-at_install')
class TestInvestigation(NhsCommon):

    def _investigation(self, **overrides):
        inc = overrides.pop('incident', None) or self._make_incident()
        vals = {
            'incident_id': inc.id, 'response_level': 'psii',
            'lead_investigator_id': self.env.user.id,
        }
        vals.update(overrides)
        return self.env['nhs.investigation'].create(vals)

    def test_submit_requires_findings(self):
        """Submission requires findings (and ToR for PSII)."""
        inv = self._investigation()
        with self.assertRaises(UserError):
            inv.action_submit()  # no ToR / findings
        inv.write({'terms_of_reference': 'Scope...', 'findings': 'Root cause X.'})
        inv.action_submit()
        self.assertEqual(inv.state, 'submitted')

    def test_approve_requires_quality_lead(self):
        """Only a Quality Lead may approve an investigation."""
        inv = self._investigation()
        inv.write({'terms_of_reference': 'Scope', 'findings': 'Findings'})
        inv.action_submit()
        with self.assertRaises(UserError):
            inv.with_user(self.user_handler).action_approve()
        inv.with_user(self.user_quality).action_approve()
        self.assertEqual(inv.state, 'approved')
        self.assertTrue(inv.approved_at)

    def test_approve_advances_incident_to_actions(self):
        """Approving the investigation advances its incident from Investigation->Actions."""
        inc = self._make_incident()
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({
            'harm_grade': 'moderate', 'response_level': 'psii'})
        inc.action_start_investigation()
        inv = inc.investigation_id
        inv.write({'terms_of_reference': 'Scope', 'findings': 'Findings'})
        inv.action_submit()
        inv.with_user(self.user_quality).action_approve()
        self.assertEqual(inv.state, 'approved')
        self.assertEqual(inc.state, 'actions')

    def test_approve_blocked_by_open_action(self):
        """Approval is blocked while an arising action is still open."""
        inv = self._investigation()
        inv.write({'terms_of_reference': 'Scope', 'findings': 'Findings'})
        inv.action_submit()
        self.env['nhs.action'].create({
            'name': 'Arising action', 'investigation_id': inv.id,
            'owner_id': self.env.user.id, 'due_date': fields.Date.today()})
        with self.assertRaises(UserError):
            inv.with_user(self.user_quality).action_approve()
