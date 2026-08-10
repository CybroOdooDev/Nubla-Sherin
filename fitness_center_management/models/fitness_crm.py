# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    diet_category_id = fields.Many2one('fitness.diet.category', string='Diet Category')
    diet_type_id = fields.Many2one('fitness.diet.type', string='Diet Type')
    birthdate = fields.Date(string='Birthdate')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    diet_description = fields.Text(string='Diet Goals / Problems')

    def action_create_diet_member(self):
        """Create a fitness member from this lead."""
        self.ensure_one()
        member = self.env['fitness.member'].create({
            'name': self.contact_name or self.partner_name or self.name,
            'email': self.email_from,
            'phone': self.phone,
            'gender': self.gender,
            'dob': self.birthdate,
            'is_diet_member': True,
            'partner_id': self.partner_id.id if self.partner_id else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fitness.member',
            'res_id': member.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_diet_plan(self):
        """Create a diet plan from this lead."""
        self.ensure_one()
        member = self.env['fitness.member'].search([
            '|',
            ('email', '=', self.email_from),
            ('partner_id', '=', self.partner_id.id),
        ], limit=1)
        if not member:
            return self.action_create_diet_member()
        plan = self.env['fitness.diet.plan'].create({
            'name': self.name or 'Diet Plan',
            'member_id': member.id,
            'diet_category_id': self.diet_category_id.id if self.diet_category_id else False,
            'diet_type_id': self.diet_type_id.id if self.diet_type_id else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fitness.diet.plan',
            'res_id': plan.id,
            'view_mode': 'form',
            'target': 'current',
        }
