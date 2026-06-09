# -*- coding: utf-8 -*-
from odoo import models, fields


class NhsRegion(models.Model):
    _inherit = 'nhs.region'

    health_system = fields.Selection(
        selection_add=[
            ('nhs_wales', 'NHS Wales'),
            ('hsc_ni', 'HSC Northern Ireland'),
        ],
        ondelete={'nhs_wales': 'set default', 'hsc_ni': 'set default'},
    )
