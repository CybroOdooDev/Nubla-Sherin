# -*- coding: utf-8 -*-
from .common import NhsEstablishmentCommon


class TestNhsFteMath(NhsEstablishmentCommon):

    def test_fte_from_hours_single_post(self):
        Post = self.env['nhs.establishment.post']
        self.assertEqual(Post._compute_fte_value(37.5, 1, 37.5), 1.0)
        self.assertEqual(Post._compute_fte_value(18.75, 1, 37.5), 0.5)

    def test_fte_from_hours_multiple_headcount(self):
        Post = self.env['nhs.establishment.post']
        # 4 full-time posts at 37.5 hrs on a 37.5 basis = 4.0 FTE
        self.assertEqual(Post._compute_fte_value(37.5, 4, 37.5), 4.0)

    def test_fte_basis_is_configurable(self):
        Post = self.env['nhs.establishment.post']
        # A 35-hour full-time basis instead of the NHS-standard 37.5
        self.assertEqual(Post._compute_fte_value(35.0, 1, 35.0), 1.0)
        self.assertEqual(Post._compute_fte_value(17.5, 1, 35.0), 0.5)

    def test_headcount_distinct_from_fte(self):
        # 20 headcount at 0.8 FTE each = 16.0 FTE total, not 20.0
        post = self._create_post(funded_fte=16.0, funded_headcount=20, in_post_fte=16.0, in_post_headcount=20)
        self.assertEqual(post.funded_fte, 16.0)
        self.assertEqual(post.funded_headcount, 20)
        self.assertNotEqual(post.funded_fte, post.funded_headcount)

    def test_onchange_prefills_fte_from_hours_and_headcount(self):
        post_form = self.env['nhs.establishment.post'].new({
            'job_title': 'Band 5 Nurse',
            'org_unit_id': self.team.id,
            'staff_group_id': self.staff_group.id,
            'band_id': self.band_5.id,
            'contracted_hours': 37.5,
            'funded_headcount': 3,
            'in_post_headcount': 2,
        })
        post_form._onchange_fte_basis()
        self.assertEqual(post_form.funded_fte, 3.0)
        self.assertEqual(post_form.in_post_fte, 2.0)
