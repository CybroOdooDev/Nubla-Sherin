/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

console.log("GLOBAL PDF PATCH LOADED");

registry.category("services").add("custom_report_patch", {
    dependencies: ["action", "notification", "bus_service"],
    async start(env, { action, notification, bus_service }) {

        bus_service.subscribe("pdf_download", (payload) => {
            if (payload.url) {
                console.log("PAYLOAD", payload);

                const orderRef = payload.order_ref || "Document";

                const link = document.createElement("a");
                link.href = payload.url;
                link.download = `${orderRef}.pdf`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                notification.add(
                    `Order - ${orderRef} downloaded successfully.`,
                    {
                        title: "Download Completed",
                        type: "success",
                    }
                );
            }
        });


        const originalDoAction = action.doAction.bind(action);

        action.doAction = async function (act, options = {}) {

            let actionId = null;
            if (typeof act === "number" || typeof act === "string") {
                actionId = parseInt(act, 10);
            } else if (typeof act === "object" && act.type === "ir.actions.report" && act.id) {
                actionId = act.id;
            }

            if (actionId) {
                const controller = env.services.action.currentController;

                let activeIds = [];

                if (options?.additionalContext?.active_ids?.length) {
                    activeIds = options.additionalContext.active_ids;
                } else if (controller?.model?.root?.selection?.length) {
                    activeIds = controller.model.root.selection.map(r => r.resId);
                } else if (controller?.props?.resId) {
                    activeIds = [controller.props.resId];
                } else if (typeof act === "object" && act.context?.active_ids?.length) {
                    activeIds = act.context.active_ids;
                }

                console.log("ACTIVE IDS:", activeIds);

                if (!activeIds.length) {
                    return originalDoAction(act, options);
                }

                const actionData = await rpc("/web/dataset/call_kw", {
                    model: "ir.actions.report",
                    method: "read",
                    args: [[actionId], ["report_name", "report_type"]],
                    kwargs: {},
                });

                if (actionData.length &&
                    actionData[0].report_type === "qweb-pdf") {

                    await rpc("/report/background_generate", {
                        report_name: actionData[0].report_name,
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
