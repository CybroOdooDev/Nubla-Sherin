/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsRecruitmentDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: null,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "nhs.vacancy",
            "get_recruitment_dashboard_data",
            []
        );
        this.state.loading = false;
    }

    openAction(resModel, views, domain = [], context = {}, name = "Details") {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: resModel,
            views: views,
            domain: domain,
            context: context,
            target: "current",
        });
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

    openOpenVacancies() {
        this.openAction(
            "nhs.vacancy",
            [[false, "list"], [false, "kanban"], [false, "form"]],
            [["state", "in", ["open", "in_progress"]]],
            {},
            "Open Vacancies"
        );
    }

    openApprovals() {
        this.openAction(
            "nhs.vacancy",
            [[false, "list"], [false, "form"]],
            [["state", "in", ["submitted", "workforce_approved"]]],
            {},
            "Awaiting Approval"
        );
    }

    openApplicationsInFlight() {
        this.openAction(
            "nhs.application",
            [[false, "kanban"], [false, "list"], [false, "form"]],
            [["stage", "not in", ["hired", "rejected", "withdrawn"]]],
            {},
            "Applications in Flight"
        );
    }

    openFunnelStage(stage) {
        this.openAction(
            "nhs.application",
            [[false, "list"], [false, "form"]],
            [["stage", "=", stage]],
            {},
            "Applications"
        );
    }

    openAgeingVacancies() {
        this.openAction(
            "nhs.vacancy",
            [[false, "list"], [false, "form"]],
            [["state", "in", ["open", "in_progress"]]],
            { search_default_group_state: 0 },
            "Vacancy Ageing"
        );
    }

    openChecksOutstanding() {
        this.openAction(
            "nhs.check",
            [[false, "list"], [false, "form"]],
            [["status", "in", ["not_started", "in_progress"]]],
            {},
            "Checks Outstanding"
        );
    }

    openChecksConcern() {
        this.openAction(
            "nhs.check",
            [[false, "list"], [false, "form"]],
            [["status", "=", "concern"]],
            {},
            "Checks — Concern"
        );
    }

    openTimeToHire() {
        this.openAction(
            "nhs.vacancy",
            [[false, "graph"], [false, "pivot"], [false, "list"]],
            [["time_to_hire", ">", 0]],
            {},
            "Time to Hire"
        );
    }
}

NhsRecruitmentDashboard.template = "odoo_nhs_recruitment.NhsRecruitmentDashboard";

registry.category("actions").add("nhs_recruitment_dashboard", NhsRecruitmentDashboard);
