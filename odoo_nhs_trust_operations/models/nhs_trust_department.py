# -*- coding: utf-8 -*-
from odoo import models, fields


class NhsTrustDepartment(models.Model):
    _name = 'nhs.trust.department'
    _description = 'NHS Trust Department'
    _order = 'site_id, name'

    name = fields.Char(
        string='Department Name',
        required=True,
        help="Department name."
    )
    code = fields.Char(
        string='Department Code',
        help="Optional internal department code used by the Trust's own systems (PAS/ESR/ledger codes)."
    )
    site_id = fields.Many2one(
        'nhs.trust.site',
        string='Parent Site',
        required=True,
        ondelete='cascade',
        index=True,
        help="Parent site. ondelete='cascade'."
    )
    trust_id = fields.Many2one(
        'nhs.trust',
        string='Trust',
        related='site_id.trust_id',
        store=True,
        index=True,
        help="Related to site_id.trust_id, stored for security rules and reporting filters."
    )
    department_type = fields.Selection([
        ('clinical', 'Clinical'),
        ('corporate', 'Corporate'),
        ('support', 'Support'),
        ('research', 'Research'),
    ],
        string='Department Type',
        required=True,
        default='clinical',
        help="Clinical = direct patient care. Corporate = HR/Finance/IT. Support = Pharmacy/Pathology/Estates. Research = R&D, trials."
    )
    specialty_id = fields.Many2one(
        'nhs.trust.specialty',
        string='Primary Specialty',
        help="Primary clinical specialty (for clinical departments)."
    )
    head_of_department_id = fields.Many2one(
        'res.partner',
        string='Head of Department',
        help="Departmental clinical or operational lead."
    )
    staff_count = fields.Integer(
        string='Staff Count',
        default=0,
        help="Headcount or FTE — the choice is per the Trust's convention. Document which one in your data entry standards."
    )
    phone = fields.Char(
        string='Phone',
        help="Department-level contact details."
    )
    email = fields.Char(
        string='Email',
        help="Department-level contact details."
    )
    description = fields.Text(
        string='Description',
        help="Free-text description."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )
