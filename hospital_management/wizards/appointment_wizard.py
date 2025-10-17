from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalAppointmentWizard(models.TransientModel):
    _name = 'hospital.appointment.wizard'
    _description = 'Quick Appointment Wizard'

    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True)
    appointment_date = fields.Date(string='Date', required=True, default=fields.Date.today)
    appointment_time = fields.Float(string='Time', required=True)
    appointment_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
    ], string='Type', required=True, default='consultation')
    reason = fields.Text(string='Reason')

    def action_create_appointment(self):
        """Create appointment from wizard"""
        appointment = self.env['hospital.appointment'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_date': self.appointment_date,
            'appointment_time': self.appointment_time,
            'appointment_type': self.appointment_type,
            'reason': self.reason,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.appointment',
            'res_id': appointment.id,
            'view_mode': 'form',
            'target': 'current',
        }