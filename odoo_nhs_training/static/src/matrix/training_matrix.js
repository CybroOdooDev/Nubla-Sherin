/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


const STATUS_COLORS = {
    compliant: "#28a745",
    due_soon: "#ffc107",
    expired: "#dc3545",
    not_done: "#adb5bd",
    exempt: "#17a2b8",
};

export class NhsTrainingMatrix extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: { subjects: [], members: [] },
            orgUnits: [],
            orgUnitId: false,
            loading: true,
        });

        onWillStart(async () => {
            this.state.orgUnits = await this.orm.searchRead(
                "nhs.org.unit", [], ["id", "complete_name"], { order: "complete_name" });
            await this.loadMatrix();
            this.state.loading = false;
        });
    }

    async loadMatrix() {
        this.state.data = await this.orm.call(
            "nhs.workforce.member", "get_training_matrix_data", [], {
                org_unit_id: this.state.orgUnitId || false,
            });
    }

    async onTeamChange(ev) {
        this.state.orgUnitId = ev.target.value ? parseInt(ev.target.value) : false;
        await this.loadMatrix();
    }

    color(status) {
        return STATUS_COLORS[status] || "#adb5bd";
    }

    async onCellClick(memberId, subjectId, cell) {
        if (cell && cell.record_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "nhs.training.record",
                res_id: cell.record_id,
                views: [[false, "form"]],
                target: "current",
            });
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.training.record",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_member_id: memberId,
                default_subject_id: subjectId,
            },
        }, {
            onClose: async () => {
                await this.loadMatrix();
            },
        });
    }

    openMember(memberId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "nhs.workforce.member",
            res_id: memberId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

NhsTrainingMatrix.template = "odoo_nhs_training.NhsTrainingMatrix";

registry.category("actions").add("nhs_training_matrix", NhsTrainingMatrix);
