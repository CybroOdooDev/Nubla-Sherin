# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from .common import NhsEstablishmentCommon


class TestNhsVacancyAge(NhsEstablishmentCommon):

    def test_days_vacant_from_start_date(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=3.0)
        thirty_days_ago = fields.Date.context_today(post) - timedelta(days=30)
        post.vacancy_start_date = thirty_days_ago
        self.assertEqual(post.days_vacant, 30)

    def test_days_vacant_zero_when_fully_staffed(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=4.0)
        self.assertEqual(post.days_vacant, 0)
        self.assertFalse(post.vacancy_start_date)

    def test_vacancy_start_date_set_automatically_on_becoming_vacant(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=4.0)
        self.assertFalse(post.vacancy_start_date)
        post.write({'in_post_fte': 3.0})
        self.assertEqual(post.vacancy_start_date, fields.Date.context_today(post))
        self.assertEqual(post.days_vacant, 0)

    def test_vacancy_start_date_cleared_when_fully_staffed_again(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=3.0)
        self.assertTrue(post.vacancy_start_date)
        post.write({'in_post_fte': 4.0})
        self.assertFalse(post.vacancy_start_date)
