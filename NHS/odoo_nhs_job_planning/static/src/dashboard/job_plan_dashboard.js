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
            await this.loadMetrics();
            this.state.loading = false;
        });
    }

    async loadMetrics(yearId) {
        this.state.metrics = await this.orm.call(
            "nhs.plan.year", "get_capacity_dashboard_metrics", [], { year_id: yearId || false });
    }

    async onChangeYear(ev) {
        const yearId = ev.target.value ? parseInt(ev.target.value, 10) : false;
        this.state.loading = true;
        await this.loadMetrics(yearId);
        this.state.loading = false;
    }

    activityBadgeClass(state) {
        if (["signed", "revised"].includes(state)) {
            return "nhs-badge-good";
        }
        if (["proposed", "in_discussion"].includes(state)) {
            return "nhs-badge-warn";
        }
        return "nhs-badge-bad";
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

    openReviewOverdue() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "in", COMPLETE_STATES],
            ["review_due_date", "<", this._today()],
        ]);
    }

    openReviewDueSoon() {
        const yearId = this.state.metrics.year_id;
        const today = this._today();
        const horizon = this._today(60);
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "in", COMPLETE_STATES],
            ["review_due_date", ">=", today], ["review_due_date", "<=", horizon],
        ]);
    }

    openOncallGaps() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "!=", "superseded"], ["oncall_profile_id", "=", false],
        ]);
    }

    openDirectorateOncallGaps(unitId) {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["org_unit_id", "=", unitId],
            ["state", "!=", "superseded"], ["oncall_profile_id", "=", false],
        ]);
    }

    _today(addDays = 0) {
        const d = new Date();
        d.setDate(d.getDate() + addDays);
        return d.toISOString().slice(0, 10);
    }

    openPaOver() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "!=", "superseded"], ["pa_balance", ">", 0.5],
        ]);
    }

    openPaUnder() {
        const yearId = this.state.metrics.year_id;
        this.openAction("nhs.job.plan", "list,form", [
            ["plan_year_id", "=", yearId], ["state", "!=", "superseded"], ["pa_balance", "<", -0.5],
        ]);
    }

    openRecentPlan(planId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.job.plan",
            views: [[false, "form"]],
            res_id: planId,
            target: "current",
        });
    }
}

NhsJobPlanDashboard.template = "odoo_nhs_job_planning.NhsJobPlanDashboard";

registry.category("actions").add("nhs_job_plan_dashboard", NhsJobPlanDashboard);
