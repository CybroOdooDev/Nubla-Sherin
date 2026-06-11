# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class NhsOdsSyncRunWizard(models.TransientModel):
    _name = 'nhs.ods.sync.run.wizard'
    _description = 'NHS ODS Sync — Run Wizard'

    mode = fields.Selection([
        ('live', 'Live (apply changes)'),
        ('dry_run', 'Dry Run (preview only)'),
    ], string='Mode', required=True, default='live')
    scope = fields.Selection([
        ('all_roles', 'All Roles'),
        ('specific_role', 'Specific Role'),
        ('specific_org', 'Specific Organisation'),
    ], string='Scope', required=True, default='all_roles')
    role_mapping_id = fields.Many2one(
        'nhs.ods.role.mapping',
        string='Role Mapping',
    )
    ods_code = fields.Char(string='ODS Code')
    delta_since = fields.Date(
        string='Delta Since',
        help="When set, only fetch orgs changed on or after this date.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        cp = self.env['ir.config_parameter'].sudo()
        default_mode = cp.get_param('nhs_ods_sync.default_mode', 'live')
        if 'mode' in fields_list:
            res['mode'] = default_mode
        return res

    def action_confirm(self):
        self.ensure_one()
        if self.scope == 'specific_role' and not self.role_mapping_id:
            raise UserError(_("Please select a role mapping for a role-specific sync."))
        if self.scope == 'specific_org' and not self.ods_code:
            raise UserError(_("Please provide an ODS code for a targeted sync."))

        run_type = 'dry_run' if self.mode == 'dry_run' else (
            'targeted' if self.scope == 'specific_org' else 'incremental' if self.delta_since else 'full'
        )

        run_vals = {
            'run_type': run_type,
            'triggered_by': 'manual',
            'user_id': self.env.user.id,
        }
        if self.delta_since:
            run_vals['delta_since'] = self.delta_since
        if self.scope == 'specific_org' and self.ods_code:
            run_vals['targeted_ods_code'] = self.ods_code.strip().upper()

        run = self.env['nhs.ods.sync.run'].create(run_vals)
        run.action_run()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Run'),
            'res_model': 'nhs.ods.sync.run',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }
