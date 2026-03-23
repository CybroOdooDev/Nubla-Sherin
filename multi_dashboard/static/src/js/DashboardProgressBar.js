/** @odoo-module **/
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const COLORS = [
    "#ffffff", "#ff9c9c", "#f7c698", "#fde388", "#bbd7f8", "#d9a8cc",
    "#f8d6c8", "#89e1db", "#97a6f9", "#ff9ecc", "#b7edbe", "#e6dbfc"
];
const GRADIENTS = [
    "linear-gradient(135deg, #ffffff 0%, #f3f4f6 100%)",
    "linear-gradient(135deg, #ff9c9c 0%, #ee5253 100%)",
    "linear-gradient(135deg, #f7c698 0%, #ff9f43 100%)",
    "linear-gradient(135deg, #fde388 0%, #feca57 100%)",
    "linear-gradient(135deg, #bbd7f8 0%, #54a0ff 100%)",
    "linear-gradient(135deg, #d9a8cc 0%, #9b59b6 100%)",
    "linear-gradient(135deg, #f8d6c8 0%, #ff9f43 100%)",
    "linear-gradient(135deg, #89e1db 0%, #00d2d3 100%)",
    "linear-gradient(135deg, #97a6f9 0%, #5d6df0 100%)",
    "linear-gradient(135deg, #ff9ecc 0%, #e91e63 100%)",
    "linear-gradient(135deg, #b7edbe 0%, #10ac84 100%)",
    "linear-gradient(135deg, #e6dbfc 0%, #5f27cd 100%)"
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
        this.notification = useService("notification");
        this.state = useState({
            data: this.props.data || {},
            aiInsight: null,
            isGettingInsight: false,
        });
    }

    // Method to get AI insight for the progress bar
    async getChartInsight() {
        if (this.state.isGettingInsight) return;
        this.state.isGettingInsight = true;

        try {
            const result = await this.orm.call(
                "multi.dashboard.charts",
                "action_get_chart_insight",
                [[this.props.data.id]],
                { date_filter: this.props.dateFilter || null }
            );

            if (result && result.success) {
                this.state.aiInsight = result.summary;
            } else {
                this.notification.add(result.error || "Failed to generate insight.", { type: "danger" });
            }
        } catch (error) {
            console.error("Error generating insight:", error);
            this.notification.add("An error occurred while generating insight.", { type: "danger" });
        } finally {
            this.state.isGettingInsight = false;
        }
    }

    // Helper to get the hex code based on the prop integer
    get accentColor() {
        const index = (this.props.data && this.props.data.todo_color) || 0;
        return index === 0 ? null : (COLORS[index] || COLORS[0]);
    }

    get backgroundStyle() {
        const index = (this.props.data && this.props.data.todo_color) || 0;
        if (this.props.data.use_background_gradient) {
            return (GRADIENTS[index] || GRADIENTS[0]);
        }
        return this.accentColor ? this.accentColor : 'var(--widget-bg)';
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
         t-attf-style="background: {{ this.backgroundStyle }}; {{ this.accentColor ? '--widget-accent: ' + this.accentColor + ';' : '' }} border-left: 5px solid rgba(0,0,0,0.1);">

        <div class="chart-header d-flex justify-content-between align-items-center">
            <div class="o_progress_title flex-grow-1" t-esc="props.widget?.name || 'Progress Bar'"/>
            <div t-if="!props.isPreview" class="progress-tools">
                <div class="chart-tool o-progress-download" title="JSON" t-on-click.stop="downloadJson">
                    <i class="fa fa-download"/>
                </div>
                <div class="chart-tool o-progress-insight" title="AI Insight" t-on-click.stop="getChartInsight">
                    <i t-att-class="state.isGettingInsight ? 'fa fa-spinner fa-spin' : 'fa fa-lightbulb-o'"/>
                </div>

                <div class="chart-tool o-progress-edit" title="Edit" t-on-click.stop="onEdit">
                    <i class="fa fa-pencil"/>
                </div>
                <div class="chart-tool o-progress-delete" title="Delete" t-on-click.stop="onDelete">
                    <i class="fa fa-trash"/>
                </div>
            </div>
        </div>

        <div class="o_progress_body flex-grow-1 d-flex gap-2 overflow-hidden">
            <div class="o_progress_main flex-grow-1 d-flex flex-column justify-content-center" style="min-width: 0;">
                <div class="d-flex justify-content-between align-items-end mb-1">
                    <span class="h3 m-0 fw-bold" t-esc="props.data.current_value"/>
                    <span class="opacity-75 small">Target: <t t-esc="props.data.target_value"/></span>
                </div>

                <div class="progress" style="height: 12px; background-color: rgba(0,0,0,0.05); border-radius: 10px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         role="progressbar"
                         t-att-style="barStyle">
                    </div>
                </div>

                <div class="text-end mt-1">
                    <span t-attf-class="small fw-bold {{isCritical ? 'text-danger' : ''}}"
                          t-esc="props.data.percentage + '%'"/>
                </div>
            </div>

            <div t-if="state.aiInsight"
                 class="progress-ai-insight-side-panel shadow-sm animate__animated animate__slideInRight flex-shrink-0">
                <div class="d-flex align-items-center mb-2">
                    <i class="fa fa-magic me-2 small"/>
                    <span class="fw-bold extra-small">AI Insight</span>
                    <button class="btn-close ms-auto shadow-none small"
                            style="transform: scale(0.6);"
                            t-on-click.stop="() => state.aiInsight = null"/>
                </div>
                <div class="progress-insight-text extra-small">
                    <t t-esc="state.aiInsight"/>
                </div>
            </div>
        </div>
    </div>
`;
