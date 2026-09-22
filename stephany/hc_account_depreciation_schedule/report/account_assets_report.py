# -*- coding: utf-8 -*-
#######################################################################################
#
#    Hai Cheung (China) Limited
#
#    Copyright (C) Hai Cheung (China) Limited.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################

from odoo import models


class AccountAssetReportHandler(models.AbstractModel):
    _inherit = 'account.asset.report.handler'

    def _query_lines(self, options):
        lines = super()._query_lines(options)

        asset_ids = {asset_id for _, asset_id, _ in lines}
        assets_by_id = {asset.id: asset for asset in self.env['account.asset'].browse(asset_ids)}

        analytic_account_ids = set()
        for asset in assets_by_id.values():
            analytic_account_ids.update(int(account_id) for account_id in (asset.analytic_distribution or {}))
        analytic_account_names = {
            account.id: account.name
            for account in self.env['account.analytic.account'].browse(analytic_account_ids)
        }

        enriched_lines = []
        for account_id, asset_id, columns_by_expr_label in lines:
            asset = assets_by_id[asset_id]
            columns_by_expr_label = dict(columns_by_expr_label)
            columns_by_expr_label['analytic_account'] = ', '.join(
                analytic_account_names[int(account_id)]
                for account_id in (asset.analytic_distribution or {})
                if int(account_id) in analytic_account_names
            )
            columns_by_expr_label['not_depreciable_value'] = asset.salvage_value
            enriched_lines.append((account_id, asset_id, columns_by_expr_label))
        return enriched_lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        for col in options['columns']:
            if col['expression_label'] == 'not_depreciable_value':
                col['name'] = ''  # The column label will be displayed in the subheader

        subheaders = options.get('custom_columns_subheaders', [])
        for subheader in subheaders:
            if subheader.get('name') == 'Characteristics':
                subheader['colspan'] += 1

        depreciation_index = next(
            (index for index, subheader in enumerate(subheaders) if subheader.get('name') == 'Depreciation'),
            len(subheaders),
        )
        subheaders.insert(depreciation_index, {"name": "Not Depreciable Value", "colspan": 1})
        options['custom_columns_subheaders'] = subheaders
