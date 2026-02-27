/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { AccountReportController } from "@account_reports/components/account_report/controller";


patch(AccountReportController.prototype, {

    async buttonAction(ev, button) {


        if (button.action === "export_file" && button.action_param === "export_to_pdf") {


            const options =
                this.model?.options          ||
                this.reportOptions           ||
                this.options                 ||
                {};

            console.log("[bg_pdf] Intercepted PDF export. options.report_id:", options.report_id);

            if (!options.report_id) {
                console.error("[bg_pdf] options.report_id is missing! options keys:", Object.keys(options));
                return super.buttonAction(ev, button);
            }

            try {
                await rpc("/report/background_generate_accounting", {
                    options: options,
                });
                this.env.services.notification.add(
                    "PDF is being generated in the background. It will download automatically when ready.",
                    { title: "PDF Generation Started", type: "success" }
                );
                return;
            } catch (e) {
                console.error("[bg_pdf] RPC failed:", e);
            }
        }

        return super.buttonAction(ev, button);
    },

});



registry.category("services").add("custom_accounting_report_bg", {
    dependencies: ["notification", "bus_service"],
    async start(env, { notification, bus_service }) {

        bus_service.subscribe("pdf_download", (payload) => {
            if (!payload?.url) return;

            const label = payload.order_ref || payload.name || "Document";

            setTimeout(() => {
                const a = document.createElement("a");
                a.href = payload.url;
                a.setAttribute("download", payload.name || `${label}.pdf`);
                a.setAttribute("target", "_self");
                document.body.appendChild(a);
                a.click();
                setTimeout(() => document.body.removeChild(a), 1000);
            }, 300);

            notification.add(`${label} is ready and downloading.`, {
                title: "Download Ready",
                type: "success",
            });
        });
    },
});