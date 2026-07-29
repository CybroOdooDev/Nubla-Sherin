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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsCommittee(models.Model):
    _name = 'nhs.committee'
    _description = 'A board, committee, sub-committee or group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True, tracking=True,
                       help="Committee name (e.g. 'Audit Committee').")
    committee_type_id = fields.Many2one('nhs.committee.type', string='Committee Type', required=True,
                                        help='board / committee / sub-committee / group / council of governors.')
    committee_type_code = fields.Selection(related='committee_type_id.code', string='Type Code', store=True,
                                           help='Convenience copy of the committee type code, used in view conditions.')
    parent_id = fields.Many2one('nhs.committee', string='Reports To', index=True, ondelete='restrict',
                                help='Reporting parent (a committee reports to the board, a sub-committee '
                                     'or group reports to a committee).')
    parent_path = fields.Char(index=True, help='Technical field storing the materialized hierarchy path.')
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True, recursive=True,
                                help='Auto-computed breadcrumb reporting line '
                                     '(e.g. "Board / Audit Committee / Charitable Funds Sub-Committee").')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company,
                                 help='Owning organisation; record rules scope on it.')
    trust_id = fields.Many2one('nhs.trust', string='Trust',
                               help='Link to the organisation in NHS Trust Management.')
    terms_of_reference = fields.Html(string='Terms of Reference',
                                     help="The committee's Terms of Reference: purpose, membership, quorum, "
                                          "frequency, delegated authority and reporting line.")
    tor_review_date = fields.Date(string='ToR Review Date', tracking=True,
                                  help='Next Terms of Reference review date (ToR are usually reviewed annually). '
                                       'A reminder is raised ahead of this date.')
    quorum_min = fields.Integer(string='Quorum (Minimum Members)', default=0,
                                help='Minimum number of present voting members for quoracy.')
    quorum_min_ned = fields.Integer(string='Quorum (Minimum NEDs)', default=0,
                                    help='Minimum number of present Non-Executive Directors required for '
                                         'quoracy, where the Terms of Reference require it.')
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('ad_hoc', 'Ad-hoc'),
    ], string='Meeting Frequency', help='How often this committee meets.')
    chair_id = fields.Many2one('nhs.director', string='Chair',
                               help='The committee chair. Selecting a chair here also adds/updates '
                                    "their Membership record with role 'Chair'.")
    member_ids = fields.One2many('nhs.committee.member', 'committee_id', string='Membership',
                                 help='Committee membership: members and their roles.')
    member_count = fields.Integer(string='Members', compute='_compute_counts',
                                  help='Total number of committee members, shown on the Members smart button.')
    voting_member_count = fields.Integer(string='Voting Members', compute='_compute_counts',
                                         help='Number of current voting members — the ceiling '
                                              'against which Quorum (Minimum Members) is checked.')
    voting_ned_count = fields.Integer(string='Voting NEDs', compute='_compute_counts',
                                      help='Number of current voting Non-Executive Directors — the '
                                           'ceiling against which Quorum (Minimum NEDs) is checked.')
    meeting_ids = fields.One2many('nhs.meeting', 'committee_id', string='Meetings',
                                  help='Meetings of this committee.')
    meeting_count = fields.Integer(string='Meeting Count', compute='_compute_counts',
                                   help='Total number of meetings held or scheduled for this committee.')
    cycle_item_ids = fields.One2many('nhs.cycle.of.business', 'committee_id', string='Cycle of Business',
                                     help='Standing items schedule for the annual cycle of business.')
    baf_risk_ids = fields.One2many('nhs.baf.risk', 'owning_committee_id', string='Principal Risks Owned',
                                   help='BAF principal risks this committee scrutinises.')
    baf_risk_count = fields.Integer(string='Principal Risks', compute='_compute_counts',
                                    help='Number of BAF principal risks owned by this committee.')
    tor_reminder_email = fields.Char(string='ToR Reminder Contact', compute='_compute_tor_reminder_email',
                                     help='Best-available recipient for the ToR-review-due reminder: '
                                          'the chair, else the committee secretary, else the company email.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('dormant', 'Dormant'),
        ('disbanded', 'Disbanded'),
    ], string='Status', default='draft', required=True, tracking=True,
       help='Committee status. New committees start as Draft until confirmed. '
            'Changes are tracked on the chatter for a full history.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Build the breadcrumb reporting-line name from the parent chain."""
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f'{rec.parent_id.complete_name} / {rec.name}'
            else:
                rec.complete_name = rec.name

    @api.depends('member_ids', 'member_ids.voting', 'member_ids.is_ned', 'meeting_ids', 'baf_risk_ids')
    def _compute_counts(self):
        """Compute member, meeting and BAF risk counts shown on smart buttons."""
        for rec in self:
            voting_members = rec.member_ids.filtered('voting')
            rec.member_count = len(rec.member_ids)
            rec.voting_member_count = len(voting_members)
            rec.voting_ned_count = len(voting_members.filtered('is_ned'))
            rec.meeting_count = len(rec.meeting_ids)
            rec.baf_risk_count = len(rec.baf_risk_ids)

    @api.depends('chair_id.email', 'member_ids.role', 'member_ids.director_id.email',
                 'company_id.email')
    def _compute_tor_reminder_email(self):
        """Pick the best-available recipient for the ToR-review-due reminder: the chair,
        else the committee secretary, else the company email — so the reminder always has
        somewhere to go, even for a committee with no chair assigned yet."""
        for rec in self:
            secretary = rec.member_ids.filtered(lambda m: m.role == 'secretary')[:1]
            rec.tor_reminder_email = (rec.chair_id.email
                                      or secretary.director_id.email
                                      or rec.company_id.email
                                      or False)

    def action_confirm(self):
        """Confirm a draft committee, moving it to Active status."""
        self.write({'state': 'active'})

    def action_disband(self):
        """Disband the committee and archive it."""
        self.write({'state': 'disbanded', 'active': False})

    def action_reactivate(self):
        """Reactivate a dormant or disbanded committee."""
        self.write({'state': 'active', 'active': True})

    def action_set_dormant(self):
        """Mark the committee as Dormant."""
        self.write({'state': 'dormant'})

    def _sync_chair_membership(self):
        """Ensure the selected chair_id has a Membership row with role='chair', and demote
        any previously-chaired member so a committee never carries two chair rows."""
        for committee in self:
            if not committee.chair_id:
                continue
            chair_member = committee.member_ids.filtered(lambda m: m.director_id == committee.chair_id)
            if chair_member:
                chair_member.filtered(lambda m: m.role != 'chair').write({'role': 'chair'})
            else:
                self.env['nhs.committee.member'].create({
                    'committee_id': committee.id,
                    'director_id': committee.chair_id.id,
                    'role': 'chair',
                })
            other_chairs = committee.member_ids.filtered(
                lambda m: m.role == 'chair' and m.director_id != committee.chair_id)
            other_chairs.write({'role': 'member'})

    @api.model_create_multi
    def create(self, vals_list):
        """Create committees and sync the chair's membership record."""
        records = super().create(vals_list)
        records.filtered('chair_id')._sync_chair_membership()
        return records

    def write(self, vals):
        """Update committees and re-sync the chair's membership when chair_id changes."""
        result = super().write(vals)
        if 'chair_id' in vals:
            self.filtered('chair_id')._sync_chair_membership()
        return result

    def action_view_meetings(self):
        """Open the list of meetings for this committee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Meetings',
            'res_model': 'nhs.meeting',
            'view_mode': 'calendar,list,form',
            'domain': [('committee_id', '=', self.id)],
            'context': {'default_committee_id': self.id},
        }

    def action_view_members(self):
        """Open the membership list for this committee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Membership',
            'res_model': 'nhs.committee.member',
            'view_mode': 'list,form',
            'domain': [('committee_id', '=', self.id)],
            'context': {'default_committee_id': self.id},
        }

    def action_open_meeting_generate_wizard(self):
        """Open the wizard to generate a series of meetings for this committee."""
        self.ensure_one()
        if self.state != 'active':
            raise UserError('Meetings can only be generated for an active committee or board.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Meeting Series',
            'res_model': 'nhs.meeting.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_committee_id': self.id,
                'default_frequency': self.frequency if self.frequency != 'ad_hoc' else 'monthly',
            },
        }

    def action_view_baf_risks(self):
        """Open the list of BAF principal risks owned by this committee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Principal Risks',
            'res_model': 'nhs.baf.risk',
            'view_mode': 'list,form',
            'domain': [('owning_committee_id', '=', self.id)],
        }

    @api.model
    def _cron_tor_review_reminder(self):
        """ToR-review-due reminder — schedule an activity for the committee secretary/chair
        for any committee whose Terms of Reference review date is within the configured
        lead time (default 30 days)."""
        lead_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_governance.tor_review_lead_days', 30))
        today = fields.Date.today()
        warn_date = today + timedelta(days=lead_days)
        committees = self.search([
            ('tor_review_date', '!=', False),
            ('tor_review_date', '<=', warn_date),
            ('state', '=', 'active'),
        ])
        template = self.env.ref('odoo_nhs_governance.mail_template_tor_review_due', raise_if_not_found=False)
        for committee in committees:
            committee.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=committee.tor_review_date,
                note=f'Terms of Reference review due for {committee.name} on {committee.tor_review_date}.',
            )
            if template and committee.tor_reminder_email:
                template.send_mail(committee.id, force_send=False)
