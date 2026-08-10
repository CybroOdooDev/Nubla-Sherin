# -*- coding: utf-8 -*-
from .common import NhsEstablishmentCommon


class TestNhsVacancy(NhsEstablishmentCommon):

    def test_part_vacant(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=3.0)
        self.assertEqual(post.vacant_fte, 1.0)
        self.assertEqual(post.vacancy_status, 'part_vacant')

    def test_fully_staffed(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=4.0)
        self.assertEqual(post.vacant_fte, 0.0)
        self.assertEqual(post.vacancy_status, 'fully_staffed')

    def test_fully_vacant(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=0.0)
        self.assertEqual(post.vacant_fte, 4.0)
        self.assertEqual(post.vacancy_status, 'fully_vacant')

    def test_over_established(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=5.0)
        self.assertEqual(post.vacant_fte, -1.0)
        self.assertEqual(post.vacancy_status, 'over_established')

    def test_recompute_on_write(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=4.0)
        self.assertEqual(post.vacancy_status, 'fully_staffed')
        post.write({'in_post_fte': 2.0})
        self.assertEqual(post.vacancy_status, 'part_vacant')
        self.assertEqual(post.vacant_fte, 2.0)

    def test_zero_funded_zero_in_post_is_fully_staffed(self):
        post = self._create_post(funded_fte=0.0, in_post_fte=0.0)
        self.assertEqual(post.vacancy_status, 'fully_staffed')
