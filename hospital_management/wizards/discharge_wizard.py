from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalDischargeWizard(models.TransientModel):
    _name = 'hospital.discharge.wizard'
    _description = 'Patient Discharge Wizard'

    admission_id = fields.Many2one('hospital.admission', string='Admission', required=True)
    discharge_date = fields.Datetime(string='Discharge Date', required=True,
                                     default=fields.Datetime.now)
    discharge_type = fields.Selection([
        ('normal', 'Normal Discharge'),
        ('against_advice', 'Against Medical Advice'),
        ('transfer', 'Transfer to Another Facility'),
        ('death', 'Death'),
    ], string='Discharge Type', required=True, default='normal')

    discharge_diagnosis = fields.Text(string='Discharge Diagnosis', required=True)
    discharge_summary = fields.Html(string='Discharge Summary')
    discharge_instructions = fields.Text(string='Discharge Instructions')
    follow_up_date = fields.Date(string='Follow-up Date')

    medications_to_continue = fields.Text(string='Medications to Continue')

    create_final_bill = fields.Boolean(string='Create Final Bill', default=True)

    def action_discharge_patient(self):
        """Discharge patient and update records"""
        self.ensure_one()

        if self.discharge_date < self.admission_id.admission_date:
            raise ValidationError(_('Discharge date cannot be before admission date.'))

        # Update admission record
        self.admission_id.write({
            'discharge_date': self.discharge_date,
            'discharge_type': self.discharge_type,
            'discharge_diagnosis': self.discharge_diagnosis,
            'discharge_summary': self.discharge_summary,
            'discharge_instructions': self.discharge_instructions,
            'follow_up_date': self.follow_up_date,
            'state': 'discharged',
        })

        # Free up the bed
        if self.admission_id.bed_id:
            self.admission_id.bed_id.write({
                'state': 'available',
                'current_patient_id': False,
                'current_admission_id': False,
            })

        # Create final bill if requested
        if self.create_final_bill:
            self._create_final_bill()

        return {'type': 'ir.actions.act_window_close'}

    def _create_final_bill(self):
        """Create final bill for admission"""
        invoice_lines = []

        # Add bed charges
        if self.admission_id.duration_days > 0:
            invoice_lines.append((0, 0, {
                'name': f'Bed Charges - {self.admission_id.ward_id.name}',
                'quantity': self.admission_id.duration_days,
                'price_unit': self.admission_id.ward_id.daily_charge,
            }))

        # Add doctor consultations
        for consultation in self.admission_id.consultation_ids:
            if not consultation.is_invoiced:
                invoice_lines.append((0, 0, {
                    'name': f'Consultation - Dr. {consultation.doctor_id.name}',
                    'quantity': 1,
                    'price_unit': consultation.doctor_id.consultation_fee,
                }))

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.admission_id.patient_id.id,
            'patient_id': self.admission_id.patient_id.id,
            'admission_id': self.admission_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        })

        return invoice