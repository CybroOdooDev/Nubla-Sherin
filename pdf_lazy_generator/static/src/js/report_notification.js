/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";

const pendingPdfRequests = new Set();

patch(ViewButton.prototype, {
    async onClick(ev) {
        const clickParams = this.props.clickParams;
        const resId = this.props.record?.resId || null;
        const actionId = clickParams?.name ? parseInt(clickParams.name, 10) : null;

        if (actionId && resId && clickParams?.type === "action") {
            try {
                const data = await rpc("/web/dataset/call_kw", {
                    model: "ir.actions.report",
                    method: "search_read",
                    args: [[["id", "=", actionId]]],
                    kwargs: { fields: ["report_name", "report_type"], limit: 1 },
                });

                if (data.length && data[0].report_type === "qweb-pdf") {
                    ev.preventDefault();
                    ev.stopPropagation();

                    const reqId = Date.now().toString(36) + Math.random().toString(36).substr(2);
                    pendingPdfRequests.add(reqId);

                    await rpc("/report/background_generate", {
                        report_name: data[0].report_name,
                        docids: [resId],
                        request_id: reqId,
                    });

                    this.env.services.notification.add(
                        "PDF generating in background...",
                        { title: "Success", type: "success" }
                    );
                    return;
                }
            } catch (e) {
                console.warn("doAction patch error:", e);
            }
        }

        return super.onClick(ev);
    }
});

registry.category("services").add("custom_report_patch", {
    dependencies: ["action", "notification", "bus_service"],
    async start(env, { action, notification, bus_service }) {

        bus_service.subscribe("pdf_download", (payload) => {
            if (!payload?.url) return;

            // Core duplicate prevention logic
            if (payload.request_id) {
                if (!pendingPdfRequests.has(payload.request_id)) {
                    return; // Ignore duplicate or already-handled downloads
                }
                pendingPdfRequests.delete(payload.request_id);
            }

            const orderRef = payload.order_ref || "Document";

            setTimeout(() => {
                const a = document.createElement("a");
                a.href = payload.url;
                a.setAttribute("download", payload.name || `${orderRef}.pdf`);
                a.setAttribute("target", "_self");
                document.body.appendChild(a);
                a.click();
                setTimeout(() => document.body.removeChild(a), 1000);
            }, 300);

            notification.add(`${orderRef} downloaded successfully.`, {
                title: "Download Completed",
                type: "success",
            });
        });

        const originalDoAction = action.doAction.bind(action);

        action.doAction = async function (act, options = {}) {
            try {
                let reportName = null;
                let activeIds = [];

                if (typeof act === "object" && act.type === "ir.actions.report") {
                    if (act.report_type === "qweb-pdf") {
                        reportName = act.report_name;
                        activeIds = act.context?.active_ids ||
                            options?.additionalContext?.active_ids ||
                            (act.context?.active_id ? [act.context.active_id] : []);
                    }
                }

                if (!reportName && (typeof act === "number" || typeof act === "string")) {
                    const actionId = parseInt(act, 10);
                    if (!isNaN(actionId)) {
                        const controller = env.services.action.currentController;
                        if (options?.additionalContext?.active_ids?.length) {
                            activeIds = options.additionalContext.active_ids;
                        } else if (controller?.model?.root?.selection?.length) {
                            activeIds = controller.model.root.selection.map(r => r.resId);
                        } else if (controller?.props?.resId) {
                            activeIds = [controller.props.resId];
                        }

                        if (activeIds.length) {
                            const data = await rpc("/web/dataset/call_kw", {
                                model: "ir.actions.report",
                                method: "search_read",
                                args: [[["id", "=", actionId]]],
                                kwargs: { fields: ["report_name", "report_type"], limit: 1 },
                            });
                            if (data.length && data[0].report_type === "qweb-pdf") {
                                reportName = data[0].report_name;
                            }
                        }
                    }
                }

                if (reportName && activeIds.length) {
                    const reqId = Date.now().toString(36) + Math.random().toString(36).substr(2);
                    pendingPdfRequests.add(reqId);

                    await rpc("/report/background_generate", {
                        report_name: reportName,
                        docids: activeIds,
                        request_id: reqId,
                    });

                    notification.add("PDF generation started in background.", {
                        title: "Success",
                        type: "success",
                    });

                    return;
                }

            } catch (e) {
                console.warn("doAction patch error:", e);
            }

            return originalDoAction(act, options);
        };
    },
});