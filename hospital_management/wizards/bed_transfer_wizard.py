from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HospitalBedTransferWizard(models.TransientModel):
    _name = 'hospital.bed.transfer.wizard'
    _description = 'Bed Transfer Wizard'

    admission_id = fields.Many2one('hospital.admission', string='Admission', required=True)
    current_bed_id = fields.Many2one('hospital.bed', string='Current Bed',
                                     related='admission_id.bed_id', readonly=True)
    current_ward_id = fields.Many2one('hospital.ward', string='Current Ward',
                                      related='admission_id.ward_id', readonly=True)

    new_ward_id = fields.Many2one('hospital.ward', string='New Ward', required=True)
    new_bed_id = fields.Many2one('hospital.bed', string='New Bed', required=True,
                                 domain="[('ward_id', '=', new_ward_id), ('state', '=', 'available')]")

    transfer_reason = fields.Text(string='Reason for Transfer', required=True)
    transfer_date = fields.Datetime(string='Transfer Date', default=fields.Datetime.now)

    def action_transfer_bed(self):
        """Transfer patient to new bed"""
        self.ensure_one()

        if self.new_bed_id.state != 'available':
            raise ValidationError(_('Selected bed is not available.'))

        # Free current bed
        self.current_bed_id.write({
            'state': 'available',
            'current_patient_id': False,
            'current_admission_id': False,
        })

        # Occupy new bed
        self.new_bed_id.write({
            'state': 'occupied',
            'current_patient_id': self.admission_id.patient_id.id,
            'current_admission_id': self.admission_id.id,
        })

        # Update admission
        self.admission_id.write({
            'ward_id': self.new_ward_id.id,
            'bed_id': self.new_bed_id.id,
        })

        # Log transfer in chatter
        self.admission_id.message_post(
            body=_("Bed transferred from %s (Bed %s) to %s (Bed %s). Reason: %s") % (
                self.current_ward_id.name,
                self.current_bed_id.bed_number,
                self.new_ward_id.name,
                self.new_bed_id.bed_number,
                self.transfer_reason
            )
        )

        return {'type': 'ir.actions.act_window_close'}