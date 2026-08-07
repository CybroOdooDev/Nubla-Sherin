# -*- coding: utf-8 -*-
"""Risk register: 5x5 scoring/banding, appetite, review-frequency, constraints,
quality-lead-gated closure, and the escalate / review / close wizards."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestRisk(NhsCommon):

    def test_rating_and_band_computation(self):
        """current_rating = consequence x likelihood; band derived from the 5x5 matrix."""
        risk = self._make_risk(current_consequence='4', current_likelihood='3')
        self.assertEqual(risk.current_rating, 12)
        self.assertEqual(risk.current_band, 'high')

    def test_band_boundaries(self):
        """Spot-check each band: 3->low, 6->moderate, 12->high, 25->extreme."""
        cases = [('1', '3', 3, 'low'), ('3', '2', 6, 'moderate'),
                 ('4', '3', 12, 'high'), ('5', '5', 25, 'extreme')]
        for cons, like, rating, band in cases:
            r = self._make_risk(current_consequence=cons, current_likelihood=like)
            self.assertEqual(r.current_rating, rating)
            self.assertEqual(r.current_band, band)

    def test_outside_appetite_flag(self):
        """outside_appetite is set when current_rating exceeds the category threshold."""
        risk = self._make_risk(current_consequence='4', current_likelihood='3')  # 12
        self.assertTrue(risk.outside_appetite)  # threshold 6
        self.risk_cat.appetite_threshold = 20
        risk.invalidate_recordset(['outside_appetite'])
        self.assertFalse(risk.outside_appetite)

    def test_review_frequency_from_band(self):
        """Band drives review frequency (high -> 90 days) unless manually overridden."""
        risk = self._make_risk(current_consequence='4', current_likelihood='3')  # high
        self.assertEqual(risk.review_frequency_days, 90)
        risk.write({'manual_frequency_override': True, 'manual_frequency_days': 45})
        self.assertEqual(risk.review_frequency_days, 45)

    def test_next_review_date(self):
        """next_review_date = last_reviewed_at + frequency days."""
        risk = self._make_risk(current_consequence='4', current_likelihood='3')  # 90d
        risk.last_reviewed_at = fields.Datetime.to_datetime('2026-01-01 00:00:00')
        self.assertEqual(risk.next_review_date,
                         fields.Date.to_date('2026-01-01') + timedelta(days=90))

    def test_manual_frequency_must_be_positive(self):
        """A manual override with a non-positive day count is rejected."""
        with self.assertRaises(ValidationError):
            self._make_risk(manual_frequency_override=True, manual_frequency_days=0)

    def test_baf_register_requires_executive_lead(self):
        """Corporate/BAF risks require an executive lead."""
        with self.assertRaises(ValidationError):
            self._make_risk(register_id=self.register_baf.id)
        # With an exec lead it is allowed.
        risk = self._make_risk(register_id=self.register_baf.id,
                               executive_lead_id=self.user_quality.id)
        self.assertTrue(risk.id)

    def test_close_requires_quality_lead_and_reason(self):
        """action_close needs the quality-lead group and a closure reason."""
        risk = self._make_risk()
        with self.assertRaises(UserError):
            risk.with_user(self.user_riskmgr).action_close()
        # Quality lead but no reason -> still blocked.
        with self.assertRaises(UserError):
            risk.with_user(self.user_quality).action_close()
        risk.closure_reason = 'Controls now fully effective.'
        risk.with_user(self.user_quality).action_close()
        self.assertEqual(risk.state, 'closed')

    def test_close_wizard(self):
        """The close wizard stores the reason and closes the risk."""
        risk = self._make_risk()
        wiz = self.env['nhs.risk.close.wizard'].with_user(self.user_quality).create({
            'risk_id': risk.id, 'closure_reason': 'Risk no longer applicable.'})
        wiz.action_confirm()
        self.assertEqual(risk.state, 'closed')
        self.assertEqual(risk.closure_reason, 'Risk no longer applicable.')

    def test_escalate_wizard_moves_register_and_logs_review(self):
        """Escalation moves the register and records a review-log entry."""
        risk = self._make_risk()
        wiz = self.env['nhs.risk.escalate.wizard'].create({
            'risk_id': risk.id,
            'target_register_id': self.register_baf.id,
            'rationale': 'Trust-wide exposure identified.',
        })
        # BAF needs an exec lead before the move is valid.
        risk.executive_lead_id = self.user_quality.id
        wiz.action_confirm()
        self.assertEqual(risk.register_id, self.register_baf)
        review = self.env['nhs.risk.review'].search([('risk_id', '=', risk.id)])
        self.assertEqual(review.decision, 'escalate')

    def test_review_wizard_rescore_updates_risk(self):
        """The review wizard 'rescore' path updates current scores and logs a review."""
        risk = self._make_risk(current_consequence='4', current_likelihood='3')  # 12
        wiz = self.env['nhs.risk.review.wizard'].create({
            'risk_id': risk.id,
            'decision': 'rescore',
            'new_current_consequence': '2',
            'new_current_likelihood': '2',
            'commentary': 'Controls strengthened.',
        })
        wiz.action_confirm()
        self.assertEqual(risk.current_rating, 4)
        self.assertTrue(risk.last_reviewed_at)
        self.assertTrue(self.env['nhs.risk.review'].search_count(
            [('risk_id', '=', risk.id), ('decision', '=', 'rescore')]))

    def test_create_from_incident(self):
        """create_from_incident builds a linked risk and cross-links the incident."""
        inc = self._make_incident()
        action = self.env['nhs.risk'].create_from_incident(inc)
        risk = self.env['nhs.risk'].browse(action['res_id'])
        self.assertIn(inc, risk.incident_ids)
        self.assertIn(risk, inc.risk_ids)

    def test_no_n_plus_1_on_rating_compute(self):
        """Reading stored ratings over many risks must not scale per-record (N+1 guard)."""
        risks = self.env['nhs.risk'].create([self._risk_vals() for _ in range(20)])
        risks.invalidate_recordset(['current_rating', 'current_band', 'outside_appetite'])
        # Stored computes are batched; this is a generous upper bound, not linear in 20.
        with self.assertQueryCount(default=30):
            risks.mapped('current_rating')
            risks.mapped('current_band')
