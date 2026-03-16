/** @odoo-module **/
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const COLORS = [
    "#ffffff", "#ff9c9c", "#f7c698", "#fde388", "#bbd7f8", "#d9a8cc",
    "#f8d6c8", "#89e1db", "#97a6f9", "#ff9ecc", "#b7edbe", "#e6dbfc"
];

export class DashboardProgressBar extends Component {
    static props = {
        widget: { type: Object },
        data: { type: Object },
        onRefresh: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        isPreview: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            data: this.props.data || {},
        });
    }

    // Helper to get the hex code based on the prop integer
    get accentColor() {
        const index = this.props.data.todo_color || 0;
        return COLORS[index] || COLORS[0];
    }

    get barStyle() {
        return `width: ${this.props.data.percentage}%;`;
    }

    get isCritical() {
        return this.props.data.percentage < 25;
    }

    async downloadJson() {
        const exportParams = { chart_id: this.props.data.id }
        try {
            const result = await this.orm.call(
                "multi.dashboard.charts",
                "export_to_json",
                [],
                exportParams
            );

            if (!result) return;

            const blob = new Blob([result.content], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error("Export failed:", error);
        }
    }

    onEdit() {
        const tileId = this.props.data.id;
        if (!tileId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts",
            res_id: tileId,
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                // Trigger a refresh. Since this is a child,
                // it's best to call a prop passed from MultiDashboard.
                if (this.props.onRefresh) {
                    await this.props.onRefresh();
                }
            }
        });
    }

    onDelete() {
        if (this.props.isPreview) {
            return;
        }
        const tileId = this.props.data.id; // Assuming you pass the record ID in props
        if (!tileId) return;

        this.orm.unlink('multi.dashboard.charts', [tileId]).then(() => {
            // it's best to call a prop passed from MultiDashboard.
            if (this.props.onDelete) {
                this.props.onDelete();
            }
        });
    }
}

DashboardProgressBar.template = xml`
    <div class="o_dashboard_progress_card shadow-sm h-100 d-flex flex-column p-3 position-relative"
         t-attf-style="background-color: {{ this.accentColor }}; border-left: 5px solid rgba(0,0,0,0.1);">

        <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="m-0 text-truncate fw-bold" t-esc="props.widget?.name || 'Progress Bar'"/>
            <t t-log='props'/>
            <div t-if="!props.isPreview" class="hover-actions btn-group btn-group-sm">
                <button class="btn btn-light border-0 opacity-75-hover"
                        title="Refresh"
                        t-on-click.prevent="props.onRefresh">
                    <i class="fa fa-refresh"/>
                </button>
                <button class="btn btn-light border-0 opacity-75-hover"
                        title="JSON"
                        t-on-click="downloadJson">
                    <i class="fa fa-download"/>
                </button>
                <button class="btn btn-light border-0 opacity-75-hover hide-btn"
                        title="Edit"
                        t-on-click="onEdit">
                    <i class="fa fa-pencil"/>
                </button>
                <button class="btn btn-light border-0 text-danger opacity-75-hover hide-btn"
                        title="Delete"
                        t-on-click="onDelete">
                    <i class="fa fa-trash"/>
                </button>
            </div>
        </div>

        <div class="flex-grow-1 d-flex flex-column justify-content-center">
            <div class="d-flex justify-content-between align-items-end mb-1">
                <span class="h3 m-0 fw-bold" t-esc="props.data.current_value"/>
                <span class="text-dark opacity-75 small">Target: <t t-esc="props.data.target_value"/></span>
            </div>

            <div class="progress" style="height: 12px; background-color: rgba(0,0,0,0.05); border-radius: 10px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     role="progressbar"
                     t-att-style="barStyle">
                </div>
            </div>

            <div class="text-end mt-1">
                <span t-attf-class="small fw-bold {{isCritical ? 'text-danger' : 'text-dark'}}"
                      t-esc="props.data.percentage + '%'"/>
            </div>
        </div>
    </div>
`;
