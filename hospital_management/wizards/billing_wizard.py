from odoo import models, fields, api, _


class HospitalBillingWizard(models.TransientModel):
    _name = 'hospital.billing.wizard'
    _description = 'Hospital Billing Wizard'

    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True)
    consultation_ids = fields.Many2many('hospital.consultation', string='Consultations')
    prescription_ids = fields.Many2many('hospital.prescription', string='Prescriptions')
    lab_request_ids = fields.Many2many('hospital.lab.request', string='Lab Tests')

    total_amount = fields.Float(string='Total Amount', compute='_compute_total')

    @api.depends('consultation_ids', 'prescription_ids', 'lab_request_ids')
    def _compute_total(self):
        for record in self:
            total = 0.0
            # Add consultation fees
            for consultation in record.consultation_ids:
                total += consultation.doctor_id.consultation_fee

            # Add prescription costs
            for prescription in record.prescription_ids:
                total += sum(prescription.prescription_line_ids.mapped('subtotal'))

            # Add lab test costs
            for lab_request in record.lab_request_ids:
                total += lab_request.test_id.price

            record.total_amount = total

    def action_create_invoice(self):
        """Create consolidated invoice"""
        invoice_lines = []

        # Add consultations
        for consultation in self.consultation_ids:
            invoice_lines.append((0, 0, {
                'name': f'Consultation - Dr. {consultation.doctor_id.name}',
                'quantity': 1,
                'price_unit': consultation.doctor_id.consultation_fee,
            }))

        # Add prescriptions
        for prescription in self.prescription_ids:
            for line in prescription.prescription_line_ids:
                invoice_lines.append((0, 0, {
                    'name': f'{line.medicine_id.name}',
                    'quantity': line.total_quantity,
                    'price_unit': line.unit_price,
                }))

        # Add lab tests
        for lab_request in self.lab_request_ids:
            invoice_lines.append((0, 0, {
                'name': f'Lab Test - {lab_request.test_id.name}',
                'quantity': 1,
                'price_unit': lab_request.test_id.price,
            }))

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.id,
            'patient_id': self.patient_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }