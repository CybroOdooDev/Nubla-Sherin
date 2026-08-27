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

ESCALATION_STATES = [
    ('needed', 'Needed'),
    ('pushed_to_bank', 'Pushed to Bank'),
    ('offered', 'Offered'),
    ('bank_filled', 'Bank-Filled'),
    ('to_agency', 'To Agency'),
    ('agency_filled', 'Agency-Filled'),
    ('manual_cover', 'Manual Cover'),
    ('cancelled', 'Cancelled'),
]

URGENCIES = [
    ('planned', 'Planned'),
    ('urgent', 'Urgent'),
    ('last_minute', 'Last Minute'),
]

# odoo_nhs_staff_bank's nhs.shift.type is a coarse rate-card classifier
# (day/night/weekend/bank holiday), distinct from this module's own richer
# nhs.roster.shift.type catalogue - map our shift category to a best-guess
# match by name rather than assuming the codes line up.
BANK_SHIFT_TYPE_HINTS = {
    'night': 'night', 'early': 'day', 'late': 'day', 'long_day': 'day',
    'twilight': 'day', 'on_call': 'day', 'other': 'day',
}


class NhsRosterEscalation(models.Model):
    """An unfilled duty escalated: pushed to the Staff Bank as an open shift
    (when installed), tracked through offered/bank-filled, and on to agency
    with cost recorded if the bank cannot fill it. Without the Staff Bank
    module, gaps simply track as unfilled/manually covered."""
    _name = 'nhs.roster.escalation'
    _inherit = ['mail.thread']
    _description = 'Roster Escalation'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', copy=False, readonly=True, default='New')
    duty_id = fields.Many2one('nhs.duty', string='Duty', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='duty_id.company_id', store=True)
    state = fields.Selection(
        ESCALATION_STATES, string='Status', required=True, default='needed', tracking=True)
    urgency = fields.Selection(URGENCIES, string='Urgency', default='planned', tracking=True)
    headcount = fields.Integer(
        string='Headcount Needed', default=1,
        help="Remaining unfilled headcount when this escalation was raised.")
    bank_shift_id = fields.Integer(
        string='Bank Shift ID', copy=False,
        help="Id of the linked odoo_nhs_staff_bank nhs.bank.shift record, if that"
             " module is installed and the escalation has been pushed. Stored as a"
             " plain id (not a relation) since Staff Bank is only a soft/runtime link.")
    bank_shift_reference = fields.Char(string='Bank Shift Reference', readonly=True)
    agency_name = fields.Char(string='Agency')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    agency_cost = fields.Monetary(string='Agency Cost', currency_field='currency_id')
    pushed_at = fields.Datetime(string='Pushed At', readonly=True)
    filled_at = fields.Datetime(string='Filled At', readonly=True)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.roster.escalation') or 'New'
        return super().create(vals_list)

    def _bank_available(self):
        return 'nhs.bank.shift' in self.env

    def _resolve_bank_shift_type(self, category):
        BankShiftType = self.env['nhs.shift.type'].sudo()
        hint = BANK_SHIFT_TYPE_HINTS.get(category, 'day')
        shift_type = BankShiftType.search([('name', 'ilike', hint)], limit=1)
        return shift_type or BankShiftType.search([], limit=1)

    def _resolve_bank_skills(self, skills):
        if not skills:
            return self.env['nhs.skill'].sudo().browse()
        BankSkill = self.env['nhs.skill'].sudo()
        matched = BankSkill.browse()
        for skill in skills:
            matched |= BankSkill.search([('name', 'ilike', skill.name)], limit=1)
        return matched

    def action_push_to_bank(self):
        """Create (or reuse) an open nhs.bank.shift for this escalation,
        source='roster'. No-op if Staff Bank isn't installed - callers
        should fall back to action_mark_manual_cover(). Field-mapping is
        best-effort (Staff Bank owns its own band/role/skill requirements
        and may reject an incomplete shift) - a failure is logged onto the
        escalation rather than raised, so one bad mapping never blocks the
        rest of a bulk/cron escalation run."""
        for escalation in self:
            if not escalation._bank_available():
                continue
            duty = escalation.duty_id
            start, end = duty.get_datetime_bounds()
            BankShift = self.env['nhs.bank.shift'].sudo()
            role = duty.demand_line_id.staff_group_id
            vals = {
                'org_unit_id': duty.unit_id.org_unit_id.id,
                'shift_start': start,
                'shift_end': end,
                'shift_type_id': escalation._resolve_bank_shift_type(
                    duty.shift_type_id.category).id,
                'headcount': escalation.headcount or 1,
                'reason': 'demand',
                'urgency': escalation.urgency or 'planned',
                'source': 'roster',
            }
            if duty.required_band_id:
                vals['band_id'] = duty.required_band_id.id
            if role:
                vals['role_id'] = role.id
            skills = escalation._resolve_bank_skills(duty.required_skill_ids)
            if skills:
                vals['skill_ids'] = [(6, 0, skills.ids)]
            try:
                bank_shift = BankShift.create(vals)
                if hasattr(bank_shift, 'action_open'):
                    bank_shift.action_open()
            except Exception as exc:  # noqa: BLE001 - Staff Bank's own validation, not ours to predict
                escalation.notes = (escalation.notes or '') + (
                    '\nCould not push to Staff Bank: %s' % exc)
                continue
            escalation.write({
                'state': 'pushed_to_bank',
                'bank_shift_id': bank_shift.id,
                'bank_shift_reference': getattr(bank_shift, 'name', str(bank_shift.id)),
                'pushed_at': fields.Datetime.now(),
            })
        return True

    def action_sync_from_bank(self):
        """Pull the linked bank shift's state back onto this escalation -
        called by cron and available as a manual button."""
        if not self._bank_available():
            return
        BankShift = self.env['nhs.bank.shift'].sudo()
        for escalation in self.filtered('bank_shift_id'):
            bank_shift = BankShift.browse(escalation.bank_shift_id).exists()
            if not bank_shift:
                continue
            bank_state = getattr(bank_shift, 'state', False)
            if bank_state == 'filled':
                escalation.write({'state': 'bank_filled', 'filled_at': fields.Datetime.now()})
            elif bank_state in ('open', 'partially_filled', 'draft'):
                escalation.state = 'offered' if bank_state == 'partially_filled' else 'pushed_to_bank'
            elif bank_state in ('to_agency', 'agency_filled'):
                escalation.state = 'to_agency' if bank_state == 'to_agency' else 'agency_filled'
                agency_cost = getattr(bank_shift, 'agency_cost', False)
                if agency_cost:
                    escalation.agency_cost = agency_cost

    def action_mark_manual_cover(self):
        self.write({'state': 'manual_cover', 'filled_at': fields.Datetime.now()})

    def action_send_to_agency(self):
        self.write({'state': 'to_agency'})

    def action_confirm_agency_filled(self, agency_name, cost):
        self.write({
            'state': 'agency_filled', 'agency_name': agency_name, 'agency_cost': cost,
            'filled_at': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _cron_auto_escalate(self):
        """Scheduled action: push unfilled duties within their unit's
        escalation lead time to the bank, when auto-escalation is on."""
        from datetime import timedelta
        today = fields.Date.context_today(self)
        Duty = self.env['nhs.duty']
        duties = Duty.search([
            ('state', 'in', ('unfilled', 'partially_filled')),
            ('period_id.state', 'in', ('in_progress', 'checked', 'approved', 'published')),
        ])
        for duty in duties:
            unit = duty.unit_id
            if not unit.escalation_auto_push or not unit.company_id.nhs_roster_auto_escalate:
                continue
            if (duty.duty_date - today).days > unit.escalation_lead_days:
                continue
            if duty.escalation_id and duty.escalation_id.state not in ('cancelled',):
                continue
            gap = duty.required_headcount - duty.assigned_count
            if gap <= 0:
                continue
            days_left = (duty.duty_date - today).days
            urgency = 'last_minute' if days_left <= 2 else ('urgent' if days_left <= 7 else 'planned')
            escalation = self.create({
                'duty_id': duty.id, 'headcount': gap, 'urgency': urgency,
            })
            if unit.escalation_auto_push:
                escalation.action_push_to_bank()

    @api.model
    def _cron_sync_from_bank(self):
        """Scheduled action: pull bank-shift state back onto every escalation
        still in flight, so the roster reflects offers/fills without waiting
        for a manual refresh."""
        escalations = self.search([
            ('state', 'in', ('pushed_to_bank', 'offered', 'to_agency')),
        ])
        escalations.action_sync_from_bank()
