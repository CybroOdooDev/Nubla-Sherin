# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from .common import NhsEstablishmentCommon


class TestNhsBandConstraint(NhsEstablishmentCommon):

    def test_band_required_unless_medical(self):
        with self.assertRaises(ValidationError):
            self._create_post(band_id=False, is_medical=False)

    def test_medical_post_does_not_require_band(self):
        post = self._create_post(band_id=False, is_medical=True, manual_indicative_salary=90000)
        self.assertFalse(post.band_id)
        self.assertEqual(post.manual_indicative_salary, 90000)

    def test_medical_post_uses_manual_pay(self):
        post = self._create_post(
            band_id=False, is_medical=True, manual_indicative_salary=95000, funded_fte=1.0)
        self.assertEqual(post.indicative_pay, 95000 * 1.0 * post.company_id.nhs_on_cost_factor)

    def test_deleted_post_exempt_from_band_requirement(self):
        post = self._create_post()
        post.with_context(nhs_change_control_apply=True).write({'status': 'deleted', 'band_id': False})
