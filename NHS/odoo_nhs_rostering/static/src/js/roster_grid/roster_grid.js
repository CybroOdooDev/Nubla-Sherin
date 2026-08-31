/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * The roster grid: staff (rows) x days (columns) for one roster period.
 * Duty cells are click-to-assign (not native drag-and-drop) - a click opens
 * a small shift-type picker that calls back into nhs.roster.period's
 * grid_assign/grid_unassign, which run the real rules engine server-side.
 * A side panel lists live open violations and each day's demand vs
 * assigned/short position.
 */
export class NhsRosterGrid extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        // `params.period_id` is only present on the initial open. A browser
        // refresh rebuilds the action from the URL, which doesn't carry
        // arbitrary client-action params but does carry `active_id` (the
        // web client encodes it specifically for this purpose) - so fall
        // back to it to keep the grid working after a refresh.
        const params = this.props.action.params || {};
        const context = this.props.action.context || {};
        this.periodId = params.period_id || context.active_id;
        this.state = useState({
            data: null,
            loading: true,
            picker: null, // { memberId, date } while the assign popover is open
            showViolations: true,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "nhs.roster.period", "get_roster_grid_data", [this.periodId]
        );
        this.state.loading = false;
    }

    shiftTypeById(id) {
        return (this.state.data.shift_types || []).find((s) => s.id === id);
    }

    cellAssignments(memberId, date) {
        return (this.state.data.assignments || []).filter(
            (a) => a.member_id === memberId && a.date === date
        );
    }

    dayDemand(date) {
        return (this.state.data.demand && this.state.data.demand[date]) || {};
    }

    dayShort(date) {
        const demand = this.dayDemand(date);
        return Object.values(demand).reduce((sum, d) => sum + (d.short || 0), 0);
    }

    memberViolations(memberId) {
        return (this.state.data.violations || []).filter((v) => v.member_id === memberId);
    }

    openPicker(memberId, date) {
        this.state.picker = { memberId, date };
    }

    closePicker() {
        this.state.picker = null;
    }

    toggleViolations() {
        this.state.showViolations = !this.state.showViolations;
    }

    async pickShiftType(shiftTypeId) {
        const { memberId, date } = this.state.picker;
        this.closePicker();
        const result = await this.orm.call(
            "nhs.roster.period", "grid_assign",
            [this.periodId, memberId, date, shiftTypeId]
        );
        if (!result.ok) {
            this.notification.add(result.error, { type: "danger", sticky: true, title: "Rule Violation" });
        }
        await this.loadData();
    }

    async unassign(memberId, date, shiftTypeId) {
        await this.orm.call(
            "nhs.roster.period", "grid_unassign",
            [this.periodId, memberId, date, shiftTypeId]
        );
        await this.loadData();
    }

    async recomputeCheck() {
        await this.orm.call("nhs.roster.period", "action_recompute_check", [[this.periodId]]);
        await this.loadData();
    }

    openPeriodForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.roster.period",
            res_id: this.periodId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

NhsRosterGrid.template = "odoo_nhs_rostering.NhsRosterGrid";

registry.category("actions").add("nhs_roster_grid", NhsRosterGrid);
