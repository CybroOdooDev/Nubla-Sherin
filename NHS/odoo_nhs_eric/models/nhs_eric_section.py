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

class NhsEricSection(models.Model):
    _name = 'nhs.eric.section'
    _description = 'ERIC Section'
    _order = 'sequence, name'

    name = fields.Char(
        string='Section Name',
        required=True,
        help='Section name (e.g. "Backlog Maintenance", "Statutory Compliance", "Occupancy Cost").'
    )
    dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        string='Data Set',
        required=True,
        ondelete='cascade',
        help='Owning data set.'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in the return.'
    )
    code = fields.Char(
        string='Section Code',
        help='Section code.'
    )
    item_def_ids = fields.One2many(
        'nhs.eric.item.def',
        'section_id',
        string='Item Definitions',
        help='Item definitions in this section.'
    )
    item_count = fields.Integer(
        string='Total Items',
        compute='_compute_item_count',
        store=True,
        help='Total item definitions in this section.'
    )

    @api.depends('item_def_ids', 'item_def_ids.change_flag')
    def _compute_item_count(self):
        """Compute number of active item definitions in this section."""
        for record in self:
            record.item_count = len(record.item_def_ids.filtered(lambda i: i.change_flag != 'removed'))

    def action_view_items(self):
        """Return an action displaying all items associated with this section.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Items',
            'res_model': 'nhs.eric.item.def',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.item_def_ids.ids)],
        }