# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class NhsOdsTestConnectionWizard(models.TransientModel):
    _name = 'nhs.ods.test.connection.wizard'
    _description = 'NHS ODS Test Connection Wizard'

    probe_ods_code = fields.Char(
        string='Probe ODS Code',
        default='RW1',
        help="ODS code used for the test probe. Default: RW1 (Manchester University NHS FT).",
    )
    result_ok = fields.Boolean(string='Connection OK', readonly=True)
    result_latency_ms = fields.Integer(string='Latency (ms)', readonly=True)
    result_message = fields.Text(string='Result', readonly=True)
    state = fields.Selection([
        ('init', 'Not tested'),
        ('success', 'Success'),
        ('warning', 'Slow'),
        ('error', 'Failed'),
    ], default='init', readonly=True)

    def action_open(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test ODS Connection'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_test(self):
        self.ensure_one()
        from ..services.ods_api_client import OdsApiClient
        client = OdsApiClient(self.env)
        ok, latency_ms, message = client.ping()
        if ok:
            if latency_ms > 2000:
                state = 'warning'
                message = f'OK but slow ({latency_ms} ms). Check network or rate limits.'
            else:
                state = 'success'
                message = f'Connected successfully in {latency_ms} ms.'
        else:
            state = 'error'
        self.write({
            'result_ok': ok,
            'result_latency_ms': latency_ms,
            'result_message': message,
            'state': state,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test ODS Connection'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
