/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { BlockUI } from "@web/core/ui/block_ui";
registry.category("ir.actions.report handlers").add("library_xlsx", async (action) => {
    if (action.report_type === 'library_xlsx') {
        const blockUI = new BlockUI();
        await download({
            url: '/library_xlsx_reports',
                data: action.data,
                complete: () => unblockUI,
                error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
    }
});
