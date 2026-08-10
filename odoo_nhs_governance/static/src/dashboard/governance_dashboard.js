/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsGovernanceDashboard extends Component {
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
            "nhs.meeting",
            "get_governance_dashboard_data",
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

    openUpcomingMeetings() {
        const todayStr = new Date().toISOString().split('T')[0];
        this.openAction(
            "nhs.meeting",
            [[false, "list"], [false, "calendar"], [false, "form"]],
            [["meeting_date", ">=", todayStr], ["state", "!=", "cancelled"]],
            {},
            "Upcoming Meetings"
        );
    }

    openInquorateMeetings() {
        this.openAction(
            "nhs.meeting",
            [[false, "list"], [false, "form"]],
            [["is_quorate", "=", false], ["state", "not in", ["scheduled", "cancelled"]]],
            {},
            "Inquorate Meetings"
        );
    }

    openOverdueActions() {
        this.openAction(
            "nhs.meeting.action",
            [[false, "list"], [false, "form"]],
            [["state", "=", "overdue"]],
            {},
            "Overdue Actions"
        );
    }

    openDoiRefreshes() {
        this.openAction(
            "res.partner",
            [[false, "list"], [false, "form"]],
            [["nhs_gov_committee_membership_ids", "!=", false]],
            {},
            "DoI Refreshes Due"
        );
    }

    openTorReviews() {
        const todayStr = new Date().toISOString().split('T')[0];
        this.openAction(
            "nhs.committee",
            [[false, "list"], [false, "form"]],
            [["tor_review_date", "!=", false], ["tor_review_date", "<=", todayStr], ["state", "=", "active"]],
            {},
            "ToR Reviews Due"
        );
    }

    openBafUnreviewed() {
        this.openAction(
            "nhs.baf.risk",
            [[false, "list"], [false, "form"]],
            [["last_reviewed", "=", false]],
            {},
            "BAF Risks Un-Reviewed"
        );
    }

    openBafStatus(band = null) {
        const domain = band ? [["current_band", "=", band]] : [];
        this.openAction(
            "nhs.baf.risk",
            [[false, "list"], [false, "pivot"], [false, "form"]],
            domain,
            { search_default_group_band: 1 },
            "BAF Risk Register"
        );
    }
}

NhsGovernanceDashboard.template = "odoo_nhs_governance.NhsGovernanceDashboard";

registry.category("actions").add("nhs_governance_dashboard", NhsGovernanceDashboard);
