from odoo import models, fields, api, _


# Extend account.move to add hospital-specific fields
class AccountMove(models.Model):
    _inherit = 'account.move'

    patient_id = fields.Many2one('hospital.patient', string='Patient', tracking=True)
    admission_id = fields.Many2one('hospital.admission', string='Admission')
    consultation_id = fields.Many2one('hospital.consultation', string='Consultation')
    insurance_claim_id = fields.Many2one('hospital.insurance.claim', string='Insurance Claim')

    is_hospital_invoice = fields.Boolean(string='Hospital Invoice', compute='_compute_is_hospital_invoice', store=True)

    @api.depends('patient_id')
    def _compute_is_hospital_invoice(self):
        for record in self:
            record.is_hospital_invoice = bool(record.patient_id)