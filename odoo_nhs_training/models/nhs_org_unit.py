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
from odoo import _, api, fields, models


class NhsOrgUnit(models.Model):
    _inherit = 'nhs.org.unit'

    member_ids = fields.One2many(
        'nhs.workforce.member',
        'org_unit_id',
        string='Workforce Members',
        help="Workforce members directly in this unit."
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        help="Live (non-leaver) members in the unit and its descendants."
    )
    team_required_count = fields.Integer(
        string='Team Required Subjects',
        compute='_compute_team_compliance',
        store=True,
        recursive=True,
        help="Sum of required subjects across members of this unit and its descendants."
    )
    team_compliant_count = fields.Integer(
        string='Team Compliant Subjects',
        compute='_compute_team_compliance',
        store=True,
        recursive=True,
    )
    team_compliance_pct = fields.Float(
        string='Team Compliance %',
        compute='_compute_team_compliance',
        store=True,
        recursive=True,
        digits=(16, 1),
        help="Training compliance % across members in this unit and its descendants."
    )

    def _compute_member_count(self):
        for unit in self:
            unit.member_count = self.env['nhs.workforce.member'].search_count([
                ('org_unit_id', 'child_of', unit.id), ('is_leaver', '=', False),
            ])

    @api.depends(
        'member_ids.compliant_subject_count', 'member_ids.required_subject_count',
        'member_ids.is_leaver', 'child_ids.team_required_count', 'child_ids.team_compliant_count',
    )
    def _compute_team_compliance(self):
        for unit in self:
            members = unit.member_ids.filtered(lambda m: not m.is_leaver)
            required = sum(members.mapped('required_subject_count'))
            compliant = sum(members.mapped('compliant_subject_count'))
            for child in unit.child_ids:
                required += child.team_required_count
                compliant += child.team_compliant_count
            unit.team_required_count = required
            unit.team_compliant_count = compliant
            unit.team_compliance_pct = (compliant / required * 100.0) if required else 100.0

    def action_view_workforce_members(self):
        self.ensure_one()
        return {
            'name': 'Workforce Members',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'list,kanban,form',
            'domain': [('org_unit_id', 'child_of', self.id)],
            'context': {'default_org_unit_id': self.id},
        }

    @api.model
    def _cron_escalate_low_compliance(self):
        """Escalate to the workforce/department lead any team whose compliance %
        has dropped below the configured target."""
        target = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.compliance_target', 85))
        template = self.env.ref(
            'odoo_nhs_training.mail_template_compliance_escalation', raise_if_not_found=False)
        units = self.search([('team_required_count', '>', 0), ('team_compliance_pct', '<', target)])
        for unit in units:
            unit.message_post(body=_(
                'Team compliance has dropped to %.1f%% (target %.0f%%).'
            ) % (unit.team_compliance_pct, target))
            if template and unit.manager_id and unit.manager_id.email:
                template.send_mail(unit.id, force_send=True)

    @api.model
    def _cron_send_weekly_digest(self):
        """Weekly compliance digest to each unit manager, plus any fallback recipients."""
        fallback = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.digest_recipients')
        units = self.search([('manager_id', '!=', False), ('team_required_count', '>', 0)])
        for unit in units:
            if not unit.manager_id.email:
                continue
            self.env['mail.mail'].sudo().create({
                'email_to': unit.manager_id.email,
                'subject': _('Weekly Training Compliance Digest — %s') % unit.complete_name,
                'body_html': (
                    '<p>Training compliance for <strong>%s</strong>: <strong>%.1f%%</strong>'
                    ' (%s of %s subjects in date).</p>'
                ) % (unit.complete_name, unit.team_compliance_pct,
                     unit.team_compliant_count, unit.team_required_count),
            }).send()
        if fallback:
            total_required = sum(self.search([]).mapped('team_required_count'))
            org_pct = 0.0
            root_units = self.search([('parent_id', '=', False)])
            if root_units:
                total_required = sum(root_units.mapped('team_required_count'))
                total_compliant = sum(root_units.mapped('team_compliant_count'))
                org_pct = (total_compliant / total_required * 100.0) if total_required else 100.0
            self.env['mail.mail'].sudo().create({
                'email_to': fallback,
                'subject': _('Weekly Training Compliance Digest — Organisation'),
                'body_html': '<p>Organisation training compliance: <strong>%.1f%%</strong>.</p>' % org_pct,
            }).send()
