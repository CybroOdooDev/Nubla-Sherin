# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

from odoo import _, fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    tab_id = fields.Char(string='Tab ID')

    def process(self):
        _logger.info("=== ProductLabelLayout.process() CALLED ===")
        _logger.info("  self.id = %s", self.id)
        _logger.info("  self.tab_id = %s", self.tab_id)
        _logger.info("  self.env.context = %s", self.env.context)

        # Log wizard fields to confirm values were saved before process() ran
        if hasattr(self, 'print_format'):
            _logger.info("  self.print_format = %s", self.print_format)
        if hasattr(self, 'product_tmpl_ids'):
            _logger.info("  self.product_tmpl_ids = %s", self.product_tmpl_ids.ids)
        if hasattr(self, 'product_ids'):
            _logger.info("  self.product_ids = %s", self.product_ids.ids)

        action = super().process()
        _logger.info("  super().process() returned: %s", action)

        if not action:
            _logger.warning("  super().process() returned nothing/False — cannot intercept")
            return action

        if not isinstance(action, dict):
            _logger.warning("  action is not a dict (type=%s) — cannot intercept", type(action))
            return action

        action_type = action.get('type')
        report_type = action.get('report_type')
        _logger.info("  action type=%s  report_type=%s", action_type, report_type)

        if action_type != 'ir.actions.report' or report_type != 'qweb-pdf':
            _logger.warning("  Not a qweb-pdf — falling back to original action")
            return action

        report_name = action.get('report_name')
        _logger.info("  report_name = %s", report_name)

        # Try every location Odoo may put docids
        docids = (
            action.get('docids')
            or action.get('context', {}).get('active_ids')
            or ([action['context']['active_id']] if action.get('context', {}).get('active_id') else [])
            or self.env.context.get('active_ids', [])
            or ([self.env.context['active_id']] if self.env.context.get('active_id') else [])
        )

        # Last resort: wizard relation fields
        if not docids:
            if hasattr(self, 'product_tmpl_ids') and self.product_tmpl_ids:
                docids = self.product_tmpl_ids.ids
                _logger.info("  docids from product_tmpl_ids: %s", docids)
            elif hasattr(self, 'product_ids') and self.product_ids:
                docids = self.product_ids.ids
                _logger.info("  docids from product_ids: %s", docids)

        _logger.info("  final docids = %s", docids)

        tab_id = self.tab_id or self.env.context.get('tab_id') or ''
        _logger.info("  tab_id = '%s'", tab_id)

        if not report_name:
            _logger.error("  NO report_name — cannot generate PDF")
            return action

        if not docids:
            _logger.error("  NO docids — cannot generate PDF")
            return action

        _logger.info("  Calling generate_in_background(report=%s, docids=%s, tab_id=%s)",
                     report_name, docids, tab_id)

        try:
            self.env['ir.actions.report'].generate_in_background(
                report_name=report_name,
                docids=list(docids),
                tab_id=tab_id,
            )
            _logger.info("  generate_in_background() called successfully")
        except Exception as e:
            _logger.exception("  generate_in_background() FAILED: %s", e)
            return action  # fallback to normal if background fails

        return {'type': 'ir.actions.act_window_close'}