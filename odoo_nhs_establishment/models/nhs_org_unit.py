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
from odoo.exceptions import UserError, ValidationError

UNIT_TYPES = [
    ('directorate', 'Directorate'),
    ('division', 'Division'),
    ('department', 'Department'),
    ('team', 'Team'),
]


class NhsOrgUnit(models.Model):
    _name = 'nhs.org.unit'
    _inherit = ['mail.thread']
    _description = "Organisational unit (directorate / division / department / team)"
    _parent_store = True
    _order = 'complete_name'
    _rec_name = 'complete_name'

    name = fields.Char(
        string='Unit Name',
        required=True,
        tracking=True,
        help="Unit name (e.g. 'Main Theatres')."
    )
    code = fields.Char(
        string='Unit Code',
        copy=False,
        help="Unit code, auto-sequenced if left blank."
    )
    unit_type = fields.Selection(
        UNIT_TYPES,
        string='Unit Type',
        required=True,
        default='team',
        tracking=True,
        help="Drives the standard hierarchy: directorate -> division -> department -> team."
             " The hierarchy itself supports unlimited depth."
    )
    parent_id = fields.Many2one(
        'nhs.org.unit',
        string='Parent Unit',
        index=True,
        ondelete='restrict',
        tracking=True,
        help="Parent unit in the organisational hierarchy."
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'nhs.org.unit',
        'parent_id',
        string='Sub-units',
        help="Units directly reporting into this one."
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        recursive=True,
        help="Breadcrumb, e.g. 'Surgery / Theatres / Main Theatres'."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company; record rules scope on it."
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Manager / Lead',
        tracking=True,
        help="Unit manager / lead."
    )
    cost_centre = fields.Many2one(
        'nhs.cost.centre',
        string='Cost Centre',
        tracking=True,
        help="Cost-centre reference for this unit."
    )
    post_ids = fields.One2many(
        'nhs.establishment.post',
        'org_unit_id',
        string='Posts',
        help="Posts directly in this unit."
    )
    funded_fte = fields.Float(
        string='Funded FTE',
        compute='_compute_establishment_totals',
        store=True,
        recursive=True,
        digits=(16, 2),
        help="Sum of funded FTE for this unit and all descendants."
    )
    in_post_fte = fields.Float(
        string='In-Post FTE',
        compute='_compute_establishment_totals',
        store=True,
        recursive=True,
        digits=(16, 2),
        help="Sum of in-post FTE, unit + descendants."
    )
    vacant_fte = fields.Float(
        string='Vacant FTE',
        compute='_compute_establishment_totals',
        store=True,
        recursive=True,
        digits=(16, 2),
        help="funded_fte - in_post_fte."
    )
    vacancy_rate = fields.Float(
        string='Vacancy Rate (%)',
        compute='_compute_establishment_totals',
        store=True,
        recursive=True,
        digits=(16, 3),
        help="vacant_fte / funded_fte as a percentage."
    )
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_post_count',
        help="Post lines under the unit (own + descendants)."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag. Archived units are hidden but retained for establishment history."
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for unit in self:
            if unit.parent_id:
                unit.complete_name = '%s / %s' % (unit.parent_id.complete_name, unit.name)
            else:
                unit.complete_name = unit.name

    @api.depends(
        'post_ids.funded_fte', 'post_ids.in_post_fte', 'post_ids.status',
        'child_ids.funded_fte', 'child_ids.in_post_fte',
    )
    def _compute_establishment_totals(self):
        for unit in self:
            posts = unit.post_ids.filtered(lambda p: p.status in ('active', 'frozen'))
            funded = sum(posts.mapped('funded_fte'))
            in_post = sum(posts.mapped('in_post_fte'))
            for child in unit.child_ids:
                funded += child.funded_fte
                in_post += child.in_post_fte
            unit.funded_fte = funded
            unit.in_post_fte = in_post
            unit.vacant_fte = funded - in_post
            unit.vacancy_rate = (unit.vacant_fte / funded) if funded else 0.0

    def _compute_post_count(self):
        for unit in self:
            unit.post_count = self.env['nhs.establishment.post'].search_count(
                [('org_unit_id', 'child_of', unit.id)])

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError('You cannot create a recursive organisational hierarchy!')

    @api.constrains('active')
    def _check_archive_with_live_posts(self):
        for unit in self:
            if unit.active:
                continue
            live_posts = unit.post_ids.filtered(lambda p: p.status in ('active', 'frozen'))
            if live_posts:
                raise ValidationError(_(
                    "You cannot archive '%(unit)s': it still has %(count)d active/frozen"
                    " post(s) assigned to it (%(refs)s).\n"
                    "Reassign those posts to another unit, or mark them as deleted first.",
                    unit=unit.complete_name,
                    count=len(live_posts),
                    refs=', '.join(live_posts.mapped('reference')[:10]),
                ))

    def unlink(self):
        for unit in self:
            blocking_posts = self.env['nhs.establishment.post'].with_context(
                active_test=False).search([('org_unit_id', '=', unit.id)])
            if blocking_posts:
                raise UserError(_(
                    "You cannot delete '%(unit)s': %(count)d post(s) are still assigned"
                    " to it (%(refs)s).\n"
                    "Reassign or delete those posts first, or archive this unit instead"
                    " of deleting it.",
                    unit=unit.complete_name,
                    count=len(blocking_posts),
                    refs=', '.join(blocking_posts.mapped('reference')[:10]),
                ))
            blocking_children = self.with_context(active_test=False).search(
                [('parent_id', '=', unit.id)])
            if blocking_children:
                raise UserError(_(
                    "You cannot delete '%(unit)s': it still has %(count)d sub-unit(s)"
                    " under it (%(names)s).\n"
                    "Delete or re-parent those sub-units first.",
                    unit=unit.complete_name,
                    count=len(blocking_children),
                    names=', '.join(blocking_children.mapped('complete_name')[:10]),
                ))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('nhs.org.unit') or 'New'
        return super().create(vals_list)

    def action_view_posts(self):
        self.ensure_one()
        return {
            'name': 'Posts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.post',
            'view_mode': 'list,kanban,form',
            'domain': [('org_unit_id', 'child_of', self.id)],
            'context': {'default_org_unit_id': self.id},
        }
