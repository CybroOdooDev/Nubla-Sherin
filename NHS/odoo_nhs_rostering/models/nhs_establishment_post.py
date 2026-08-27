# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class NhsEstablishmentPost(models.Model):
    """Extends the Establishment post with a flag for whether it takes part
    in e-Rostering. v1 targets the general staff-rostering problem (nursing,
    AHP, admin, support) - medical posts default off, since consultants/SAS
    doctors work to a job plan, not a rota (see the Job Planning module,
    a separate roadmap item)."""
    _inherit = 'nhs.establishment.post'

    nhs_rosterable = fields.Boolean(
        string='Rostered',
        default=True,
        help="This post's holders can be assigned duties on an e-Rostering roster."
             " Untick for Medical / Non-AfC posts that are job-planned rather than"
             " rostered (advisory flag only, not enforced by the rules engine)."
    )
