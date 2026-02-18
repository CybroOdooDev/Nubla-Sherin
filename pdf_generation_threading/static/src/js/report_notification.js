/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

console.log("CUSTOM REPORT PATCH LOADED");

registry.category("services").add("custom_report_patch", {
    dependencies: ["action", "notification"],
    async start(env, { action, notification }) {

        const originalDoAction = action.doAction.bind(action);

        action.doAction = async function (act, options = {}) {

            console.log("ACTION OBJECT:", act);

            if (typeof act === "number") {

                if (act === 313) {

                    const activeIds =
                        env.services.action.currentController?.props?.context?.active_ids || [];

                    await rpc("/report/background_generate", {
                        report_name: "stock.report_picking_type_label",
                        docids: activeIds,
                    });

                    notification.add(
                        "PDF generation started in background.",
                        {
                            title: "Success",
                            type: "success",
                        }
                    );

                    return;
                }
            }

            return originalDoAction(act, options);
        };
    },
});
