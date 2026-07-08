/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsTrainingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });

        onWillStart(async () => {
            this.state.metrics = await this.orm.call(
                "nhs.workforce.member", "get_training_dashboard_metrics", []);
            this.state.loading = false;
        });
    }

    openAction(resModel, viewMode, domain, context) {
        const views = viewMode.split(",").map((mode) => [false, mode]);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Details",
            res_model: resModel,
            views,
            domain: domain || [],
            context: context || {},
            target: "current",
        });
    }

    openAllMembers() {
        this.openAction("nhs.workforce.member", "list,kanban,form");
    }

    openNonCompliant() {
        this.openAction("nhs.workforce.member", "list,kanban,form",
            [["compliance_status", "=", "non_compliant"]]);
    }

    openDueSoon() {
        this.openAction("nhs.training.record", "list,form",
            [["status", "=", "due_soon"], ["is_latest", "=", true]]);
    }

    openExpired() {
        this.openAction("nhs.training.record", "list,form",
            [["status", "=", "expired"], ["is_latest", "=", true]]);
    }

    openLapsedRegistrations() {
        this.openAction("nhs.registration", "list,form", [["status", "=", "lapsed"]]);
    }

    openRecord(resModel, resId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

NhsTrainingDashboard.template = "odoo_nhs_training.NhsTrainingDashboard";

registry.category("actions").add("nhs_training_dashboard", NhsTrainingDashboard);
