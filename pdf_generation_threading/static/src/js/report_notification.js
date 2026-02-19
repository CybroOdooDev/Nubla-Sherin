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

        action.doAction = function (act, options = {}) {
            console.log("INTERCEPTING ACTION (NEW):", act);

            let actionId = null;
            if (typeof act === "number") {
                actionId = act;
            } else if (typeof act === "string") {
                actionId = act;
            } else if (act && typeof act === "object" && act.id) {
                actionId = act.id;
            }

            // Check if it's already a report action object
            if (act && typeof act === "object" && (act.type === "ir.actions.report" || act.report_type === "qweb-pdf")) {
                console.log("ALREADY A REPORT ACTION OBJECT, DETACHING...");
                this._handleBackgroundReport(act, options);
                return Promise.resolve();
            }

            if (actionId) {
                // If we have an ID, we need to check its type. 
                // To avoid blocking the UI, we'll return a Promise that resolves after we check.
                // But wait, if we return early, we might miss the chance to run the original action if it's NOT a report.

                // Better approach: start checking in background, but don't hold up the UI if it's definitely a report.
                // For now, let's try to resolve the type check as fast as possible.

                return (async () => {
                    try {
                        const actionData = await rpc("/web/dataset/call_kw", {
                            model: "ir.actions.report",
                            method: "read",
                            args: [[actionId], ["report_name", "report_type"]],
                            kwargs: {},
                        }, { silent: true });

                        if (actionData.length && actionData[0].report_type === "qweb-pdf") {
                            console.log("REPORT ACTION DETECTED VIA ID, DETACHING...");
                            this._handleBackgroundReport(actionData[0], options);
                            return; // Resolves the outer async function's promise
                        }
                    } catch (e) {
                        console.error("Error checking report action:", e);
                    }
                    return originalDoAction(act, options);
                })();
            }

            return originalDoAction(act, options);
        };

        action._handleBackgroundReport = async function (actionData, options) {
            console.log("HANDLING BACKGROUND REPORT:", actionData);
            const controller = env.services.action.currentController;

            let activeIds = [];
            if (options.active_ids) {
                activeIds = options.active_ids;
            } else if (controller?.model?.root?.selection?.length) {
                activeIds = controller.model.root.selection.map(r => r.resId);
            } else if (controller?.props?.resId) {
                activeIds = [controller.props.resId];
            }

            console.log("ACTIVE IDS FOR BACKGROUND:", activeIds);

            if (activeIds.length) {
                try {
                    await rpc("/report/background_generate", {
                        report_name: actionData.report_name,
                        docids: activeIds,
                    }, { silent: true });

                    notification.add(
                        "PDF generation started in background.",
                        {
                            title: "Success",
                            type: "success",
                        }
                    );
                } catch (e) {
                    console.error("Error generating background report:", e);
                }
            }
        };
    },
});
