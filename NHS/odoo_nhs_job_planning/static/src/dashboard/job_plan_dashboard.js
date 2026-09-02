/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const COMPLETE_STATES = ["signed", "revised"];
const OPEN_ENDED_STATES = ["proposed", "in_discussion"];

export class NhsJobPlanDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });

        onWillStart(async () => {
            this.state.metrics = await this.orm.call(
                "nhs.plan.year", "get_capacity_dashboard_metrics", []);
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

    openAllPlans() {
        this.action.doAction("odoo_nhs_job_planning.action_nhs_job_plan_team");
    }

    openGaps() {
        this.action.doAction("odoo_nhs_job_planning.action_nhs_establishment_post_jobplan_gaps");
    }

    openDirectorateGaps(unitId) {
        this.openAction("nhs.establishment.post", "list,form", [
            ["is_medical", "=", true], ["status", "=", "active"], ["org_unit_id", "=", unitId],
            "|", ["job_plan_state", "=", false], ["job_plan_state", "not in", COMPLETE_STATES],
        ]);
    }

    openUnsigned() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "not in", [...COMPLETE_STATES, "superseded"]],
        ]);
    }

    openStalled() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "in", OPEN_ENDED_STATES],
        ]);
    }

    openDirectoratePlans(unitId) {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["org_unit_id", "=", unitId], ["state", "in", COMPLETE_STATES],
        ]);
    }
}

NhsJobPlanDashboard.template = "odoo_nhs_job_planning.NhsJobPlanDashboard";

registry.category("actions").add("nhs_job_plan_dashboard", NhsJobPlanDashboard);
