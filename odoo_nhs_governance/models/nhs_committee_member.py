# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsCommitteeMember(models.Model):
    _name = 'nhs.committee.member'
    _description = 'NHS Committee Membership'
    _order = 'committee_id, role, director_id'

    committee_id = fields.Many2one(
        'nhs.committee',
        required=True,
        ondelete='cascade',
        help="Committee, board or group the person sits on.",
    )
    company_id = fields.Many2one(
        related='committee_id.company_id',
        store=True,
        help="Owning company inherited from the committee.",
    )
    director_id = fields.Many2one(
        'nhs.director',
        string='Director / Officer',
        help="Governance person record for this member.",
    )
    partner_id = fields.Many2one(
        'res.partner',
        help="Contact for external members or attendees who are not Odoo users.",
    )
    user_id = fields.Many2one(
        'res.users',
        help="Odoo user used for member access to packs, actions and declarations.",
    )
    role = fields.Selection([
        ('chair', 'Chair'),
        ('vice_chair', 'Vice Chair'),
        ('member', 'Member'),
        ('attendee', 'Attendee'),
        ('in_attendance', 'In Attendance'),
        ('secretary', 'Secretary'),
    ], required=True, default='member', help="Role held on this committee, such as chair, member, attendee or secretary.")
    is_ned = fields.Boolean(
        string='Non-Executive Director',
        help="Marks the member as a non-executive director for NED quorum rules.",
    )
    term_start = fields.Date(help="Start date of this committee membership term.")
    term_end = fields.Date(help="End date or expected end date of this committee membership term.")
    voting = fields.Boolean(
        default=True,
        string='Counts to Quorum',
        help="Whether this member votes and counts toward meeting quoracy.",
    )
    attendance_expectation = fields.Float(
        string='Attendance Expectation %',
        default=75.0,
        help="Expected attendance level used for board-effectiveness attendance monitoring.",
    )
    active = fields.Boolean(default=True, help="Archive flag for ended or inactive memberships.")

    def name_get(self):
        result = []
        for rec in self:
            name = rec.director_id.name or rec.partner_id.name or rec.user_id.name or rec.role
            if rec.committee_id:
                name = '%s - %s' % (name, rec.committee_id.name)
            result.append((rec.id, name))
        return result
