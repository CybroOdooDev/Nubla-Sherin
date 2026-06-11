# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

PROVENANCE_WATCHED_FIELDS = (
    'name', 'ods_code', 'state', 'street', 'street2', 'city', 'zip', 'phone',
    'establishment_date', 'foundation_trust', 'trust_type_id',
)


class NhsTrust(models.Model):
    _inherit = 'nhs.trust'

    ods_org_id = fields.Many2one(
        'nhs.ods.organisation',
        string='ODS Cache Entry',
        ondelete='set null',
        help="Reverse link to the cached ODS payload.",
    )
    ods_last_synced_at = fields.Datetime(
        string='Last ODS Sync',
        help="Timestamp of the most recent successful sync that touched this trust.",
    )
    ods_provenance_ids = fields.One2many(
        'nhs.ods.field.provenance',
        'trust_id',
        string='Field Provenance',
    )
    ods_pending_conflict_count = fields.Integer(
        string='Pending Conflicts',
        compute='_compute_ods_pending_conflict_count',
        help="Count of open ODS conflicts on this trust.",
    )

    def _compute_ods_pending_conflict_count(self):
        for trust in self:
            trust.ods_pending_conflict_count = self.env['nhs.ods.sync.conflict'].search_count([
                ('trust_id', '=', trust.id),
                ('state', '=', 'pending'),
            ])

    @api.constrains('health_system', 'icb_id', 'health_board_id', 'region_id')
    def _check_geographic_fields(self):
        if self.env.context.get('nhs_ods_sync'):
            return
        return super()._check_geographic_fields()

    @api.constrains('health_system', 'icb_id', 'health_board_id', 'welsh_lhb_id', 'region_id', 'trust_type_id')
    def _check_governance_link(self):
        if self.env.context.get('nhs_ods_sync'):
            return
        return super()._check_governance_link()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('nhs_ods_sync'):
            for record, vals in zip(records, vals_list):
                record._upsert_provenance(vals, source='manual')
        return records

    def write(self, vals):
        if self.env.context.get('nhs_ods_sync') and 'state' in vals:
            state = vals.pop('state')
            result = super().write(vals)
            super(models.Model, self).write({'state': state})
            vals['state'] = state
        else:
            result = super().write(vals)
        if not self.env.context.get('nhs_ods_sync'):
            for record in self:
                record._upsert_provenance(vals, source='manual')
        return result

    def _upsert_provenance(self, vals, source):
        Provenance = self.env['nhs.ods.field.provenance'].sudo()
        sync_run = self.env.context.get('nhs_ods_sync_run_id')
        for fname in PROVENANCE_WATCHED_FIELDS:
            if fname not in vals:
                continue
            existing = Provenance.search([
                ('trust_id', '=', self.id),
                ('field_name', '=', fname),
            ], limit=1)
            prov_vals = {
                'source': source,
                'last_updated_at': fields.Datetime.now(),
            }
            if source == 'manual':
                prov_vals['last_updated_by_user_id'] = self.env.user.id
            elif source == 'ods' and sync_run:
                prov_vals['last_sync_run_id'] = sync_run
            if existing:
                existing.write(prov_vals)
            else:
                Provenance.create({
                    'trust_id': self.id,
                    'field_name': fname,
                    **prov_vals,
                })

    def action_refresh_from_ods(self):
        self.ensure_one()
        if not self.ods_code:
            from odoo.exceptions import UserError
            raise UserError(_("This trust has no ODS code — cannot refresh from ODS."))
        if self.ods_org_id:
            self.ods_org_id.refresh_from_ods()
            self.ods_org_id.apply_to_trust()
        else:
            ods_org = self.env['nhs.ods.organisation'].search([('ods_code', '=', self.ods_code)], limit=1)
            if ods_org:
                ods_org.refresh_from_ods()
                ods_org.apply_to_trust()
        self.ods_last_synced_at = fields.Datetime.now()

    def action_view_provenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Field Provenance'),
            'res_model': 'nhs.ods.field.provenance',
            'view_mode': 'list',
            'domain': [('trust_id', '=', self.id)],
            'context': {'default_trust_id': self.id},
        }

    def action_view_conflicts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('ODS Conflicts'),
            'res_model': 'nhs.ods.sync.conflict',
            'view_mode': 'kanban,list,form',
            'domain': [('trust_id', '=', self.id), ('state', '=', 'pending')],
            'context': {'default_trust_id': self.id},
        }
