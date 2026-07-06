# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class NhsEstablishmentCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.nhs_change_control_single_stage = False
        cls.company.nhs_change_control_required = True
        cls.directorate = cls.env['nhs.org.unit'].create({
            'name': 'Surgery', 'unit_type': 'directorate',
        })
        cls.division = cls.env['nhs.org.unit'].create({
            'name': 'Theatres', 'unit_type': 'division', 'parent_id': cls.directorate.id,
        })
        cls.department = cls.env['nhs.org.unit'].create({
            'name': 'Main Theatres', 'unit_type': 'department', 'parent_id': cls.division.id,
        })
        cls.team = cls.env['nhs.org.unit'].create({
            'name': 'Theatre 3 Nursing Team', 'unit_type': 'team', 'parent_id': cls.department.id,
        })
        cls.staff_group = cls.env.ref('odoo_nhs_establishment.staff_group_nursing_midwifery')
        cls.band_5 = cls.env.ref('odoo_nhs_establishment.afc_band_5')
        cls.band_6 = cls.env.ref('odoo_nhs_establishment.afc_band_6')
        cls.group_manager = cls.env.ref('odoo_nhs_establishment.group_nhs_workforce_manager')
        cls.group_officer = cls.env.ref('odoo_nhs_establishment.group_nhs_workforce_officer')
        cls.group_user = cls.env.ref('base.group_user')
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Workforce Manager', 'login': 'wf_manager',
            'email': 'wf.manager@test.nhs.uk',
            'group_ids': [(6, 0, [cls.group_manager.id, cls.group_user.id])],
        })
        cls.officer_user = cls.env['res.users'].create({
            'name': 'Workforce Officer', 'login': 'wf_officer',
            'email': 'wf.officer@test.nhs.uk',
            'group_ids': [(6, 0, [cls.group_officer.id, cls.group_user.id])],
        })

    def _create_post(self, **overrides):
        vals = {
            'job_title': 'Band 5 Theatre Nurse',
            'org_unit_id': self.team.id,
            'staff_group_id': self.staff_group.id,
            'band_id': self.band_5.id,
            'funded_fte': 4.0,
            'funded_headcount': 4,
            'in_post_fte': 3.0,
            'in_post_headcount': 3,
            'status': 'active',
        }
        vals.update(overrides)
        return self.env['nhs.establishment.post'].create(vals)
