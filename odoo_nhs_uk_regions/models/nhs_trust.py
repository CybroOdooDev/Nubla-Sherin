# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NhsTrust(models.Model):
    _inherit = 'nhs.trust'

    health_system = fields.Selection(
        selection_add=[
            ('nhs_wales', 'NHS Wales'),
            ('hsc_ni', 'HSC Northern Ireland'),
        ],
        ondelete={'nhs_wales': 'set default', 'hsc_ni': 'set default'},
    )
    welsh_lhb_id = fields.Many2one(
        'nhs.welsh.lhb',
        string='Local Health Board (Wales)',
        index=True,
        ondelete='restrict',
        help="Welsh Local Health Board. Required when health_system='nhs_wales' (except national Welsh trusts).",
    )

    @api.onchange('health_system')
    def _onchange_health_system(self):
        res = super()._onchange_health_system()
        if self.health_system == 'nhs_wales':
            self.icb_id = False
            self.ics_id = False
            self.health_board_id = False
            return {
                'domain': {
                    'region_id': [('health_system', '=', 'nhs_wales')],
                    'trust_type_id': [('health_system', 'in', ('nhs_wales', 'both'))],
                }
            }
        elif self.health_system == 'hsc_ni':
            self.icb_id = False
            self.ics_id = False
            self.health_board_id = False
            self.welsh_lhb_id = False
            return {
                'domain': {
                    'region_id': [('health_system', '=', 'hsc_ni')],
                    'trust_type_id': [('health_system', 'in', ('hsc_ni', 'both'))],
                }
            }
        else:
            self.welsh_lhb_id = False
        return res

    @api.constrains('health_system', 'icb_id', 'health_board_id', 'welsh_lhb_id', 'region_id', 'trust_type_id')
    def _check_governance_link(self):
        for trust in self:
            sys = trust.health_system
            if trust.region_id and trust.region_id.health_system != sys:
                raise ValidationError(_(
                    "Region '%s' does not belong to the selected health system."
                ) % trust.region_id.name)
            if sys == 'nhs_england':
                if not trust.icb_id:
                    raise ValidationError(_("English trusts must have an ICB."))
                if trust.health_board_id or trust.welsh_lhb_id:
                    raise ValidationError(_("English trusts cannot have a Welsh LHB or Scottish Health Board."))
            elif sys == 'nhs_scotland':
                if not trust.health_board_id:
                    raise ValidationError(_("Scottish trusts must have a Health Board."))
                if trust.icb_id or trust.ics_id or trust.welsh_lhb_id:
                    raise ValidationError(_("Scottish trusts cannot have an English ICB/ICS or Welsh LHB."))
            elif sys == 'nhs_wales':
                is_national = trust.trust_type_id.code in ('WELSH_NATIONAL', 'WELSH_SHA')
                if not is_national and not trust.welsh_lhb_id:
                    raise ValidationError(_(
                        "Welsh trusts must have a Local Health Board unless they are a national trust "
                        "(e.g. WAST, Velindre, PHW)."
                    ))
                if trust.icb_id or trust.ics_id or trust.health_board_id:
                    raise ValidationError(_("Welsh trusts cannot have an English ICB/ICS or Scottish Health Board."))
            elif sys == 'hsc_ni':
                if trust.icb_id or trust.ics_id or trust.health_board_id or trust.welsh_lhb_id:
                    raise ValidationError(_("NI HSC Trusts cannot have any intermediate body."))
