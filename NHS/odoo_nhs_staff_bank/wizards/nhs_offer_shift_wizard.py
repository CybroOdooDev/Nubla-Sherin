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
from datetime import timedelta
from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsOfferShiftWizard(models.TransientModel):
    """Offer a shift to eligible bank members — broadcast to everyone eligible,
    or targeted to specific members picked by the coordinator. Ineligible
    members are listed too, greyed out, with the reason they can't be offered."""
    _name = 'nhs.offer.shift.wizard'
    _description = 'Offer Shift Wizard'

    shift_id = fields.Many2one('nhs.bank.shift', string='Shift', required=True)
    broadcast = fields.Boolean(
        string='Broadcast to All Eligible', default=True,
        help="Offer to every eligible+compliant member at once. Untick to hand-pick"
             " specific members instead (targeted).")
    expiry_hours = fields.Integer(
        string='Offer Expires In (Hours)',
        default=lambda self: self.env.company.nhs_bank_offer_expiry_hours or 24,
    )
    line_ids = fields.One2many('nhs.offer.shift.wizard.line', 'wizard_id', string='Candidates')

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the candidate lines from the shift's eligible members,
        pre-selecting those who are eligible and not already offered."""
        res = super().default_get(fields_list)
        shift_id = res.get('shift_id') or self.env.context.get('default_shift_id')
        if shift_id:
            shift = self.env['nhs.bank.shift'].browse(shift_id)
            already_offered = shift.offer_ids.filtered(
                lambda o: o.response in ('pending', 'accepted')).member_id
            already_booked = self.env['nhs.shift.booking'].search([
                ('state', 'in', ('booked', 'worked')),
                ('shift_start', '<', shift.shift_end),
                ('shift_end', '>', shift.shift_start),
            ]).member_id
            skip = already_offered | already_booked
            lines = []
            for outcome in shift.get_eligible_members():
                member = outcome['member']
                reasons = outcome['reasons']
                if member in already_booked and member not in already_offered:
                    reasons = reasons + ['Already has a booking that overlaps this shift.']
                lines.append((0, 0, {
                    'member_id': member.id,
                    'eligible': outcome['eligible'] and member not in already_booked,
                    'reasons': '; '.join(reasons),
                    'already_offered': member in skip,
                    'selected': outcome['eligible'] and member not in skip,
                }))
            res['line_ids'] = lines
        return res

    def action_send_offers(self):
        """Create shift offers for the selected (or all eligible, if broadcast)
        candidates, snapshotting eligibility as the audit record."""
        self.ensure_one()
        if self.broadcast:
            targets = self.line_ids.filtered(lambda l: l.eligible and not l.already_offered)
        else:
            targets = self.line_ids.filtered(lambda l: l.selected and not l.already_offered)
            ineligible = targets.filtered(lambda l: not l.eligible)
            if ineligible:
                raise UserError((
                    "Cannot offer to ineligible member(s): %s") % ', '.join(
                    ineligible.mapped('member_id.name')))
        if not targets:
            raise UserError(("No eligible candidates to offer this shift to."))
        expiry = fields.Datetime.now() + timedelta(hours=self.expiry_hours or 24)
        offers = self.env['nhs.shift.offer']
        for line in targets:
            offers |= self.env['nhs.shift.offer'].create({
                'shift_id': self.shift_id.id,
                'member_id': line.member_id.id,
                'expiry_datetime': expiry,
            })
        template = self.env.ref('odoo_nhs_staff_bank.mail_template_shift_offer', raise_if_not_found=False)
        no_email = self.env['nhs.bank.member']
        for offer in offers:
            if template and offer.member_id.email:
                mail_id = template.send_mail(offer.id, force_send=True)
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                self.shift_id.message_post(
                    subject=mail.subject,
                    body=Markup(mail.body_html) if mail.body_html else (
                        "Shift offer emailed to %s." % offer.member_id.name),
                    subtype_xmlid='mail.mt_note',
                )
            else:
                no_email |= offer.member_id
        if no_email:
            self.shift_id.message_post(
                body="Shift offer created but not emailed (no email on file) for: %s" % (
                    ', '.join(no_email.mapped('name'))),
                subtype_xmlid='mail.mt_note',
            )
        return {'type': 'ir.actions.act_window_close'}


class NhsOfferShiftWizardLine(models.TransientModel):
    """A single candidate row in the Offer Shift wizard: one bank member,
    their eligibility outcome, and whether to send them an offer."""
    _name = 'nhs.offer.shift.wizard.line'
    _description = 'Offer Shift Wizard Candidate Line'

    wizard_id = fields.Many2one('nhs.offer.shift.wizard', ondelete='cascade')
    member_id = fields.Many2one('nhs.bank.member', string='Member', required=True)
    eligible = fields.Boolean(string='Eligible', readonly=True)
    reasons = fields.Char(string='Reason / Warning', readonly=True)
    already_offered = fields.Boolean(
        string='Already Offered / Booked', readonly=True,
        help="True if the member already has a pending/accepted offer, or an"
             " existing booking that overlaps this shift.")
    selected = fields.Boolean(string='Offer')
