/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsBankDashboard extends Component {
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
            "nhs.bank.shift",
            "get_bank_dashboard_data",
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

    openOpenShifts() {
        this.openAction(
            "nhs.bank.shift",
            [[false, "kanban"], [false, "list"], [false, "form"]],
            [["state", "in", ["open", "partially_filled"]]],
            {}, "Open Shifts"
        );
    }

    openUrgentShifts() {
        this.openAction(
            "nhs.bank.shift",
            [[false, "list"], [false, "form"]],
            [["urgency", "in", ["urgent", "last_minute"]], ["state", "in", ["open", "partially_filled"]]],
            {}, "Urgent / Last-Minute Shifts"
        );
    }

    openFilledShifts() {
        this.openAction(
            "nhs.bank.shift",
            [[false, "list"], [false, "form"]],
            [["state", "=", "filled"]],
            {}, "Filled Shifts"
        );
    }

    openAgencyShifts() {
        this.openAction(
            "nhs.bank.shift",
            [[false, "list"], [false, "form"]],
            [["state", "=", "to_agency"]],
            {}, "Shifts Gone to Agency"
        );
    }

    openComplianceExposure() {
        this.openAction(
            "nhs.bank.member",
            [[false, "list"], [false, "form"]],
            [["compliance_status", "=", "non_compliant"]],
            {}, "Compliance Exposure"
        );
    }

    openAnalytics() {
        this.action.doAction("odoo_nhs_staff_bank.action_nhs_bank_shift_analytics");
    }
}

NhsBankDashboard.template = "odoo_nhs_staff_bank.NhsBankDashboard";

registry.category("actions").add("nhs_bank_dashboard", NhsBankDashboard);
