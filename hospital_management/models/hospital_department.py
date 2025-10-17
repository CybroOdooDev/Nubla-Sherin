from odoo import models, fields, api, _


class HospitalDepartment(models.Model):
    _name = 'hospital.department'
    _description = 'Hospital Department'
    _order = 'name'

    name = fields.Char(string='Department Name', required=True)
    code = fields.Char(string='Department Code', required=True)
    description = fields.Text(string='Description')
    head_doctor_id = fields.Many2one('hospital.doctor', string='Head of Department')

    # Relationships
    doctor_ids = fields.One2many('hospital.doctor', 'department_id', string='Doctors')
    ward_ids = fields.One2many('hospital.ward', 'department_id', string='Wards')

    # Statistics
    doctor_count = fields.Integer(string='Number of Doctors', compute='_compute_doctor_count')
    bed_count = fields.Integer(string='Total Beds', compute='_compute_bed_count')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    def _compute_doctor_count(self):
        for record in self:
            record.doctor_count = len(record.doctor_ids)

    def _compute_bed_count(self):
        for record in self:
            record.bed_count = sum(record.ward_ids.mapped('bed_ids').mapped('capacity'))