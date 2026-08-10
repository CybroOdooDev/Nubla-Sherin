# -*- coding: utf-8 -*-
from .common import NhsEstablishmentCommon


class TestNhsIndicativePay(NhsEstablishmentCommon):

    def test_indicative_pay_from_band(self):
        post = self._create_post(band_id=self.band_5.id, funded_fte=4.0)
        expected = self.band_5.indicative_salary * 4.0 * self.company.nhs_on_cost_factor
        self.assertEqual(post.indicative_pay, expected)

    def test_indicative_pay_with_on_cost_factor(self):
        self.company.nhs_on_cost_factor = 1.2
        post = self._create_post(band_id=self.band_5.id, funded_fte=2.0)
        self.assertEqual(post.indicative_pay, self.band_5.indicative_salary * 2.0 * 1.2)

    def test_indicative_pay_from_manual_medical_value(self):
        post = self._create_post(
            band_id=False, is_medical=True, manual_indicative_salary=80000, funded_fte=1.0)
        self.assertEqual(post.indicative_pay, 80000 * 1.0 * self.company.nhs_on_cost_factor)

    def test_indicative_pay_recomputes_on_fte_change(self):
        post = self._create_post(band_id=self.band_5.id, funded_fte=1.0)
        base_pay = post.indicative_pay
        post.with_context(nhs_change_control_apply=True).write({'funded_fte': 2.0})
        self.assertEqual(post.indicative_pay, base_pay * 2.0)
