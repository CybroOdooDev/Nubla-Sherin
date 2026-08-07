/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsDsptDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });

        onWillStart(async () => {
            this.state.metrics = await this.orm.call(
                "nhs.dspt.assessment", "get_dspt_dashboard_data", []);
            this.state.loading = false;
        });
    }

    getRateLevel(rate) {
        if (rate >= 80) {
            return "good";
        }
        if (rate >= 50) {
            return "warn";
        }
        return "bad";
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

    openAssessment() {
        if (!this.state.metrics.assessment_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.dspt.assessment",
            res_id: this.state.metrics.assessment_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openGaps() {
        this.openAction("nhs.dspt.evidence", "list,form", [
            ["assessment_id", "=", this.state.metrics.assessment_id],
            ["is_mandatory", "=", true],
            ["status", "=", "not_met"],
        ]);
    }

    openOverdueActions() {
        this.openAction("nhs.dspt.action", "list,form", [
            ["assessment_id", "=", this.state.metrics.assessment_id],
            ["is_overdue", "=", true],
        ]);
    }

    openStaleEvidence() {
        this.openAction("nhs.dspt.evidence", "list,form", [
            ["assessment_id", "=", this.state.metrics.assessment_id],
            ["is_stale", "=", true],
        ]);
    }

    openStandard(standardId) {
        this.openAction("nhs.dspt.evidence", "list,form", [
            ["assessment_id", "=", this.state.metrics.assessment_id],
            ["standard_id", "=", standardId],
        ]);
    }

    openOwner(ownerId) {
        this.openAction("nhs.dspt.evidence", "list,form", [
            ["assessment_id", "=", this.state.metrics.assessment_id],
            ["owner_id", "=", ownerId],
        ]);
    }
}

NhsDsptDashboard.template = "odoo_nhs_dspt.NhsDsptDashboard";

registry.category("actions").add("nhs_dspt_dashboard", NhsDsptDashboard);
