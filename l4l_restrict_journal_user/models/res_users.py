# -*- coding: utf-8 -*-
################################################################################
#
#	Cats and Dogs Solution
#
#	Copyright (C) Cats and Dogs Solution.
#
#	This program is under the terms of the Odoo Proprietary License v1.0
#	(OPL-1)
#	It is forbidden to publish, distribute, sublicense, or sell copies of the
#	Software or modified copies of the Software.
#
################################################################################

from odoo import api, models, fields


class Users(models.Model):
    _inherit = "res.users"

    allowed_journal_ids = fields.Many2many('account.journal', string="Journals", context={'bypass_domain_access': True})
    restrict_journal_enabled = fields.Boolean(
        string="Restrict Journal Enabled",
        compute="_compute_restrict_journal_enabled",
        store=True)

    @api.depends('groups_id')
    def _compute_restrict_journal_enabled(self):
        for user in self:
            user.restrict_journal_enabled = user.has_group('l4l_restrict_journal_user.access_restrict_user_for_journal')

    def _get_allowed_journals(self):
        """Return allowed journals or all if none set."""
        self.ensure_one()
        if self.has_group('l4l_restrict_journal_user.access_restrict_user_for_journal'):
            if self.allowed_journal_ids:
                return self.allowed_journal_ids
            # fallback → if no journals assigned, allow all
            return self.env['account.journal'].search([])
        return self.env['account.journal'].search([])
