# -*- coding: utf-8 -*-
from .common import NhsEstablishmentCommon


class TestNhsRollup(NhsEstablishmentCommon):

    def test_rollup_post_to_organisation(self):
        self._create_post(funded_fte=4.0, in_post_fte=3.0)
        other_team = self.env['nhs.org.unit'].create({
            'name': 'Theatre 4 Nursing Team', 'unit_type': 'team', 'parent_id': self.department.id,
        })
        self._create_post(org_unit_id=other_team.id, funded_fte=2.0, in_post_fte=2.0)

        self.assertEqual(self.team.funded_fte, 4.0)
        self.assertEqual(self.team.in_post_fte, 3.0)
        self.assertEqual(self.team.vacant_fte, 1.0)

        self.assertEqual(self.department.funded_fte, 6.0)
        self.assertEqual(self.department.in_post_fte, 5.0)
        self.assertEqual(self.department.vacant_fte, 1.0)

        self.assertEqual(self.division.funded_fte, 6.0)
        self.assertEqual(self.directorate.funded_fte, 6.0)

    def test_vacancy_rate_rollup(self):
        self._create_post(funded_fte=4.0, in_post_fte=2.0)
        self.assertEqual(self.team.vacancy_rate, 0.5)
        self.assertEqual(self.department.vacancy_rate, 0.5)

    def test_rollup_recomputes_on_change(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=3.0)
        self.assertEqual(self.directorate.funded_fte, 4.0)
        post.write({'in_post_fte': 4.0})
        self.assertEqual(self.directorate.in_post_fte, 4.0)
        self.assertEqual(self.directorate.vacant_fte, 0.0)

    def test_deleted_post_excluded_from_rollup(self):
        post = self._create_post(funded_fte=4.0, in_post_fte=4.0)
        self.assertEqual(self.team.funded_fte, 4.0)
        post.with_context(nhs_change_control_apply=True).write({'status': 'deleted', 'active': False})
        self.assertEqual(self.team.funded_fte, 0.0)
