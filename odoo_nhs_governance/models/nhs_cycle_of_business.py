# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsCycleOfBusiness(models.Model):
    _name = 'nhs.cycle.of.business'
    _description = 'NHS Committee Cycle of Business'
    _order = 'committee_id, sequence, title'

    committee_id = fields.Many2one(
        'nhs.committee',
        required=True,
        ondelete='cascade',
        help="Committee this standing cycle item belongs to.",
    )
    company_id = fields.Many2one(
        related='committee_id.company_id',
        store=True,
        help="Owning company inherited from the committee.",
    )
    sequence = fields.Integer(default=10, help="Ordering position in the committee cycle of business.")
    title = fields.Char(required=True, help="Standing item title, for example Annual Accounts or BAF Review.")
    frequency = fields.Selection([
        ('every_meeting', 'Every Meeting'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], default='annually', help="How often this standing item should come to the committee.")
    scheduled_months = fields.Char(help='Comma-separated month numbers, for example 3,6,9,12.')
    purpose = fields.Selection([
        ('decision', 'Decision'),
        ('assurance', 'Assurance'),
        ('information', 'Information'),
        ('discussion', 'Discussion'),
    ], default='assurance', help="Purpose of the standing item when it is added to an agenda.")
    owner_director_id = fields.Many2one(
        'nhs.director',
        string='Owner / Presenter',
        help="Director or officer responsible for bringing this item to committee.",
    )
    is_statutory = fields.Boolean(help="Flags statutory or annual obligations on the governance calendar.")
    active = fields.Boolean(default=True, help="Archive flag for standing items no longer in the cycle.")

    def is_due_for_meeting(self, meeting):
        self.ensure_one()
        if self.frequency in ('every_meeting', 'monthly'):
            return True
        if not meeting.meeting_date:
            return False
        meeting_month = fields.Datetime.context_timestamp(meeting, meeting.meeting_date).month
        months = [int(month.strip()) for month in (self.scheduled_months or '').split(',') if month.strip().isdigit()]
        if months:
            return meeting_month in months
        return self.frequency == 'quarterly' and meeting_month in (3, 6, 9, 12)
