/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { status } from "@odoo/owl";

if (!window.customReportTabId) {
    window.customReportTabId = Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}
const UNIQUE_TAB_ID = window.customReportTabId;


async function getReportInfo(actionId, rpcService) {
    if (!isNaN(parseInt(actionId))) {
        const data = await rpcService("/web/dataset/call_kw", {
            model: "ir.actions.report",
            method: "search_read",
            args: [[["id", "=", parseInt(actionId)]]],
            kwargs: { fields: ["report_name", "report_type"], limit: 1 },
        });
        return data.length ? data[0] : null;
    }

    if (typeof actionId === "string" && actionId.includes(".")) {
        const data = await rpcService("/web/dataset/call_kw", {
            model: "ir.actions.report",
            method: "search_read",
            args: [[["report_name", "like", actionId.split(".")[1]]]],
            kwargs: { fields: ["report_name", "report_type"], limit: 1 },
        });
        if (data.length) return data[0];

        const action = await rpcService("/web/action/load", {
            action_id: actionId,
        });
        if (action?.report_type === "qweb-pdf") {
            return { report_name: action.report_name, report_type: action.report_type };
        }
    }

    return null;
}


patch(ViewButton.prototype, {
    async onClick(ev) {
        const clickParams = this.props.clickParams;
        const resId = this.props.record?.resId || null;
        const actionId = clickParams?.name || null;
        const isPrintButton = this.props.string?.toLowerCase().includes("print") || actionId?.toLowerCase().includes("print");
        const isXmlId = typeof actionId === "string" && actionId.includes(".");
        const isNumeric = !isNaN(parseInt(actionId)) && !isNaN(actionId);

        if (actionId && resId && (clickParams?.type === "action" || (clickParams?.type === "object" && isPrintButton))) {
            if (clickParams?.type === "object") {
                this.env.services.notification.add(
                    "Processing print request...",
                    { type: "info", sticky: false }
                );
                return super.onClick(ev);
            }

            if (isXmlId || isNumeric) {
                try {
                    const report = await getReportInfo(actionId, this.env.services.rpc);
                    if (report?.report_type === "qweb-pdf") {
                        ev.preventDefault();
                        ev.stopPropagation();

                        await this.env.services.rpc("/report/background_generate", {
                            report_name: report.report_name,
                            docids: [resId],
                            tab_id: UNIQUE_TAB_ID,
                        });

                        this.env.services.notification.add(
                            "PDF generating in background.",
                            { title: "Success", type: "success" }
                        );
                        return;
                    }
                } catch (e) {
                    console.warn("ViewButton action patch error:", e);
                }
            }
        }

        if (status(this) === "destroyed") {
            return;
        }

        return super.onClick(ev);
    }
});


registry.category("services").add("custom_report_patch", {
    dependencies: ["action", "notification", "bus_service"],
    async start(env, { action, notification, bus_service }) {

        bus_service.subscribe("pdf_download", (payload) => {
            if (!payload?.url) return;
            if (payload.tab_id !== UNIQUE_TAB_ID) return;

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
                if (!act) {
                    return originalDoAction(act, options);
                }

                // Inject tab_id into the context so wizards can access it
                const tabContext = { tab_id: UNIQUE_TAB_ID };
                if (typeof act === "object") {
                    act.context = Object.assign({}, act.context || {}, tabContext);
                }
                options.additionalContext = Object.assign({}, options.additionalContext || {}, tabContext);

                let reportName = null;
                let activeIds = [];

                if (typeof act === "object" && act.type === "ir.actions.report") {
                    if (act.report_type === "qweb-pdf") {
                        reportName = act.report_name;

                        const ctxActiveIds = act.context?.active_ids;
                        const optActiveIds = options?.additionalContext?.active_ids;
                        let actionDocIds = act.docids || act.res_ids || [];
                        if (actionDocIds && !Array.isArray(actionDocIds)) {
                            actionDocIds = [actionDocIds];
                        }

                        activeIds = Array.isArray(ctxActiveIds) ? ctxActiveIds : [];
                        if (!activeIds.length && Array.isArray(optActiveIds)) {
                            activeIds = optActiveIds;
                        }
                        if (!activeIds.length && actionDocIds && actionDocIds.length) {
                            activeIds = actionDocIds;
                        }
                        if (!activeIds.length && act.context?.active_id) {
                            activeIds = [act.context.active_id];
                        }
                        if (!activeIds.length && act.res_id) {
                            activeIds = [act.res_id];
                        }
                    }
                }

                if (!reportName) {
                    const isNumeric = typeof act === "number" ||
                        (typeof act === "string" && !isNaN(parseInt(act)) && !act.includes("."));
                    const isXmlId = typeof act === "string" && act.includes(".");

                    if (isNumeric || isXmlId) {
                        const report = await getReportInfo(act, action.env ? action.env.services.rpc : env.services.rpc);
                        if (report?.report_type === "qweb-pdf") {
                            reportName = report.report_name;
                        }
                    }
                }

                if (reportName && !activeIds.length) {
                    const controller = env.services.action.currentController;
                    if (options?.additionalContext?.active_ids?.length) {
                        activeIds = options.additionalContext.active_ids;
                    } else if (controller?.model?.root?.selection?.length) {
                        activeIds = controller.model.root.selection.map(r => r.resId);
                    } else if (controller?.model?.root?.resId) {
                        activeIds = [controller.model.root.resId];
                    } else if (controller?.props?.resId) {
                        activeIds = [controller.props.resId];
                    }
                }

                if (reportName && activeIds.length) {
                    // Fire and forget RPC
                    env.services.rpc("/report/background_generate", {
                        report_name: reportName,
                        docids: activeIds,
                        tab_id: UNIQUE_TAB_ID,
                    }).catch(e => console.warn("Background RPC error:", e));

                    notification.add("PDF generation started in background.", {
                        title: "Success",
                        type: "success",
                    });
                    return true;
                }

            } catch (e) {
                console.warn("doAction patch error:", e);
            }

            return originalDoAction(act, options);
        };
    },
});
