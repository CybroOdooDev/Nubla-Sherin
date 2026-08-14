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
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NhsBankRate(models.Model):
    """Bank pay rate card, by band/role and shift type, effective-dated so it
    can be revised as pay awards change without hard-coding a value.
    Reference data — never a Python constant."""
    _name = 'nhs.bank.rate'
    _description = 'Bank Rate Card (effective-dated)'
    _order = 'band_id, effective_from desc'

    name = fields.Char(
        string='Rate Label',
        required=True,
        help="Rate label, e.g. 'Band 5 Night — Ward'."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company; pay rates are company-specific."
    )
    band_id = fields.Many2one(
        'nhs.afc.band',
        string='Band',
        help="Agenda for Change band the rate applies to. Leave blank for a"
             " role-only (non-AfC) rate."
    )
    role = fields.Char(
        string='Role',
        help="Role the rate is specific to, where relevant (e.g. 'Registered Nurse')."
             " Leave blank for a band-wide rate."
    )
    shift_type_id = fields.Many2one(
        'nhs.shift.type',
        string='Shift Type',
        help="Day / night / weekend / bank holiday. Leave blank for a rate that"
             " applies regardless of shift type."
    )
    hourly_rate = fields.Monetary(
        string='Hourly Rate',
        required=True,
        currency_field='currency_id',
        help="Bank pay rate per hour, before any enhancement."
    )
    enhancement_pct = fields.Float(
        string='Enhancement (%)',
        digits=(16, 2),
        help="Unsocial-hours/enhancement uplift applied on top of the hourly rate."
    )
    effective_from = fields.Date(
        string='Effective From',
        required=True,
        default=fields.Date.context_today,
        help="Date this rate becomes valid. Rates change with pay awards, so this"
             " is versioned reference data rather than a single hard-coded value."
    )
    effective_to = fields.Date(
        string='Effective To',
        help="Date this rate stops applying. Leave blank for an open-ended,"
             " currently-effective rate."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency for the rate."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    @api.constrains('effective_from', 'effective_to')
    def _check_date_range(self):
        """Reject a rate whose end date is before its start date."""
        for rate in self:
            if rate.effective_to and rate.effective_from and rate.effective_to < rate.effective_from:
                raise ValidationError(
                    "The 'Effective To' date cannot be before 'Effective From'.")

    @api.model
    def _find_rate(self, band_id=False, role=False, shift_type_id=False, date=None, company_id=False):
        """Resolve the single best-matching effective rate for a band/role/shift-type
        combination on a given date, preferring the most specific match
        (band + role + shift type) down to the least specific (band only).
        Returns an empty recordset if nothing matches.
        """
        date = date or fields.Date.context_today(self)
        domain = [
            ('company_id', '=', company_id or self.env.company.id),
            ('effective_from', '<=', date),
            '|', ('effective_to', '=', False), ('effective_to', '>=', date),
        ]
        candidates = self.search(domain)
        if band_id:
            candidates = candidates.filtered(lambda r: not r.band_id or r.band_id.id == band_id)
        if shift_type_id:
            candidates = candidates.filtered(
                lambda r: not r.shift_type_id or r.shift_type_id.id == shift_type_id)
        if role:
            role_candidates = candidates.filtered(lambda r: r.role and r.role.strip().lower() == role.strip().lower())
            generic_candidates = candidates.filtered(lambda r: not r.role)
        else:
            role_candidates = self.browse()
            generic_candidates = candidates.filtered(lambda r: not r.role)

        def _score(rate):
            return (bool(rate.band_id), bool(rate.role), bool(rate.shift_type_id))

        pool = (role_candidates or generic_candidates)
        if band_id:
            pool = pool.filtered(lambda r: r.band_id and r.band_id.id == band_id) or pool
        pool = pool.sorted(key=_score, reverse=True)
        return pool[:1]

    def compute_payable(self, hours):
        """Payable amount for `hours` worked at this rate, enhancement included."""
        self.ensure_one()
        base = hours * self.hourly_rate
        return base * (1 + (self.enhancement_pct or 0.0) / 100.0)
