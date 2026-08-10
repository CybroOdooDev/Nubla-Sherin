from odoo import models, fields, api


class NhsWard(models.Model):
    _name = 'nhs.ward'
    _description = 'NHS Ward / Department'
    _order = 'name'

    name = fields.Char(string='Ward Name', required=True)
    code = fields.Char(string='Ward Code')
    ward_type = fields.Selection([
        ('general', 'General Medical'),
        ('surgical', 'Surgical'),
        ('icu', 'Intensive Care (ICU)'),
        ('hdu', 'High Dependency (HDU)'),
        ('paediatric', 'Paediatric'),
        ('maternity', 'Maternity'),
        ('mental_health', 'Mental Health'),
        ('emergency', 'Emergency / A&E'),
        ('outpatient', 'Outpatient'),
        ('day_surgery', 'Day Surgery'),
        ('rehab', 'Rehabilitation'),
        ('oncology', 'Oncology'),
        ('cardiology', 'Cardiology'),
        ('other', 'Other'),
    ], string='Ward Type', default='general', required=True)
    specialty = fields.Char(string='Clinical Specialty')
    capacity = fields.Integer(string='Bed Capacity')
    location = fields.Char(string='Building / Floor')
    phone = fields.Char(string='Ward Phone')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Trust', default=lambda self: self.env.company
    )
    note = fields.Text(string='Notes')

    patient_ids = fields.One2many('epic.patient', 'ward_id', string='Patients')
    patient_count = fields.Integer(
        compute='_compute_patient_count', string='Current Patients', store=False
    )

    @api.depends('patient_ids.active', 'patient_ids.discharge_date')
    def _compute_patient_count(self):
        for ward in self:
            ward.patient_count = self.env['epic.patient'].search_count([
                ('ward_id', '=', ward.id),
                ('active', '=', True),
                ('discharge_date', '=', False),
            ])

    def action_view_patients(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Patients — {self.name}',
            'res_model': 'epic.patient',
            'view_mode': 'list,form',
            'domain': [('ward_id', '=', self.id)],
            'context': {'default_ward_id': self.id},
        }
