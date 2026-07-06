# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from .common import NhsEstablishmentCommon


class TestNhsChangeControl(NhsEstablishmentCommon):

    def test_direct_fte_edit_blocked_when_controlled(self):
        post = self._create_post()
        self.company.nhs_change_control_required = True
        with self.assertRaises(UserError):
            post.write({'funded_fte': 5.0})

    def test_direct_fte_edit_allowed_when_not_controlled(self):
        post = self._create_post()
        self.company.nhs_change_control_required = False
        post.write({'funded_fte': 5.0})
        self.assertEqual(post.funded_fte, 5.0)

    def test_increase_fte_change_applies_on_approval(self):
        post = self._create_post(funded_fte=4.0)
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'increase_fte',
            'post_id': post.id,
            'proposed_fte': 6.0,
            'reason': 'Extra clinic demand',
        })
        self.assertTrue(change.name.startswith('ECR'))
        change.action_submit()
        change.with_user(self.manager_user).action_workforce_approve()
        change.with_user(self.manager_user).action_finance_approve()
        change.with_user(self.manager_user).action_apply()
        self.assertEqual(post.funded_fte, 6.0)
        self.assertEqual(change.state, 'applied')

    def test_officer_cannot_approve(self):
        post = self._create_post(funded_fte=4.0)
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'increase_fte', 'post_id': post.id,
            'proposed_fte': 6.0, 'reason': 'Demand',
        })
        change.action_submit()
        with self.assertRaises(UserError):
            change.with_user(self.officer_user).action_workforce_approve()

    def test_rejected_change_does_not_apply(self):
        post = self._create_post(funded_fte=4.0)
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'increase_fte', 'post_id': post.id,
            'proposed_fte': 8.0, 'reason': 'Speculative',
        })
        change.action_submit()
        change.rejection_reason = 'Not affordable this year'
        change.action_reject()
        self.assertEqual(change.state, 'rejected')
        self.assertEqual(post.funded_fte, 4.0)

    def test_create_post_change_creates_new_post(self):
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'create_post',
            'org_unit_id': self.team.id,
            'proposed_job_title': 'Band 6 Sister',
            'proposed_staff_group_id': self.staff_group.id,
            'proposed_band_id': self.band_6.id,
            'proposed_fte': 1.0,
            'proposed_headcount': 1,
            'reason': 'New sister post agreed with finance',
        })
        change.action_submit()
        change.with_user(self.manager_user).action_workforce_approve()
        change.with_user(self.manager_user).action_finance_approve()
        change.with_user(self.manager_user).action_apply()
        self.assertTrue(change.post_id)
        self.assertEqual(change.post_id.job_title, 'Band 6 Sister')
        self.assertEqual(change.post_id.funded_fte, 1.0)

    def test_single_stage_approval_skips_finance_step(self):
        self.company.nhs_change_control_single_stage = True
        post = self._create_post(funded_fte=4.0)
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'increase_fte', 'post_id': post.id,
            'proposed_fte': 5.0, 'reason': 'Single stage test',
        })
        change.action_submit()
        change.with_user(self.manager_user).action_workforce_approve()
        self.assertEqual(change.state, 'finance_approved')
        change.with_user(self.manager_user).action_apply()
        self.assertEqual(post.funded_fte, 5.0)

    def test_cost_impact_computed_for_increase_fte(self):
        post = self._create_post(band_id=self.band_5.id, funded_fte=4.0)
        change = self.env['nhs.establishment.change'].create({
            'change_type': 'increase_fte', 'post_id': post.id,
            'proposed_fte': 5.0, 'reason': 'Budget approved',
        })
        expected = self.band_5.indicative_salary * (5.0 - 4.0) * self.company.nhs_on_cost_factor
        self.assertEqual(change.cost_impact, expected)
