/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsRosterDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "nhs.roster.period", "get_roster_dashboard_data", []
        );
        this.state.loading = false;
    }

    openPeriod(periodId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.roster.period",
            res_id: periodId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openViolations(severity) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: severity === "hard" ? "Hard Violations" : "Soft Violations",
            res_model: "nhs.rule.violation",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "open"], ["severity", "=", severity]],
            target: "current",
        });
    }

    openEscalations() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Escalations",
            res_model: "nhs.roster.escalation",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "not in", ["bank_filled", "agency_filled", "manual_cover", "cancelled"]]],
            target: "current",
        });
    }
}

NhsRosterDashboard.template = "odoo_nhs_rostering.NhsRosterDashboard";

registry.category("actions").add("nhs_roster_dashboard", NhsRosterDashboard);
