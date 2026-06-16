from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NhsLocation(models.Model):
    _name = 'nhs.location'
    _description = 'Physical Location (site → unit/ward → room)'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('nhs.location', string='Parent Location',
                                index=True, ondelete='restrict')
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True)
    location_type = fields.Selection([
        ('site', 'Site'),
        ('unit', 'Unit / Ward'),
        ('room', 'Room'),
        ('external', 'External'),
    ], string='Type', required=True, default='unit')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)
    default_handler_id = fields.Many2one('res.users', string='Default Handler')
    active = fields.Boolean(default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f'{rec.parent_id.complete_name} / {rec.name}'
            else:
                rec.complete_name = rec.name

    @api.constrains('parent_id')
    def _check_depth(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id and rec.parent_id.parent_id.parent_id:
                raise ValidationError('Locations support a maximum of 3 levels (site → unit → room).')

    def name_get(self):
        return [(r.id, r.complete_name) for r in self]
