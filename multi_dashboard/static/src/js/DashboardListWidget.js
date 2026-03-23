/** @odoo-module */
import { Component, xml, useState } from "@odoo/owl";
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

function getOnAccentColor(hexColor) {
    const hex = (hexColor || "").trim().replace("#", "");
    if (hex.length !== 6) {
        return "#111827";
    }
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const l = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    return l > 0.65 ? "#111827" : "#ffffff";
}

// This component is designed to be used inside the MultiDashboard widget.
export class DashboardListWidget extends Component {
    setup() {
        this.state = useState({
            currentPage: 1,
            expandedGroups: {},
            aiInsight: null,
            isGettingInsight: false,
        });
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
    }

    // Method to get AI insight for the list widget
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

    // --- Edit Actions ---
    onEdit() {
        const listId = this.props.data.id; // Assuming you pass the record ID in props
        if (!listId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts", // Your model name
            res_id: listId,
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

    // --- Delete Actions ---
    onDelete() {
        const listId = this.props.data.id; // Assuming you pass the record ID in props
        if (!listId) return;

        this.orm.unlink('multi.dashboard.charts', [listId]).then(() => {
            // it's best to call a prop passed from MultiDashboard.
            if (this.props.onDelete) {
                this.props.onDelete();
            }
        });
    }

    // --- Pagination Getters (unchanged) ---
    get limitPerPage() {
        return this.props.data.limit_per_page || 10;
    }

    // Calculate total pages based on the number of records and limit per page
    get totalPages() {
        const totalRecords = this.props.data.records.length;
        return Math.ceil(totalRecords / this.limitPerPage);
    }

    // Get the records to display for the current page
    get paginatedRecords() {
        const start = (this.state.currentPage - 1) * this.limitPerPage;
        const end = start + this.limitPerPage;
        return this.props.data.records.slice(start, end);
    }

    // Helper getters to determine if we're on the first or last page
    get isFirstPage() {
        return this.state.currentPage === 1;
    }

    // Helper getters to determine if we're on the first or last page
    get isLastPage() {
        return this.state.currentPage === this.totalPages;
    }

    // --- Actions ---
    setPage(direction) {
        if (direction === 'next' && !this.isLastPage) {
            this.state.currentPage++;
        } else if (direction === 'prev' && !this.isFirstPage) {
            this.state.currentPage--;
        }
    }

    // Toggle the expanded state of a group
    toggleGroup(groupName) {
        // Toggle the boolean value for the specific group
        if (this.state.expandedGroups[groupName]) {
            this.state.expandedGroups[groupName] = false;
        } else {
            this.state.expandedGroups[groupName] = true;
        }
    }

    // Handle row click to open the form view of the record
    onRowClick(record) {
        // If it's a preview, do nothing
        if (this.props.isPreview) {
            return;
        }
        if (this.props.data.row_clickable) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: this.props.data.model,
                res_id: record.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    // --- Download JSON ---
    downloadJson() {
        if (this.props.isPreview) {
            return;
        }
        this.downloadJsonExport({ chart_id: this.props.data.id });
    }

    // This method calls the server to get the JSON export content and triggers a download in the browser.
    async downloadJsonExport(exportParams) {
        /**
         * exportParams can be:
         * { dashboard_id: 1 } OR { chart_id: 5 }
         */
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

    // Keep list widgets readable in dark dashboards by using a light accent surface.
    get accentColor() {
        const index = this.props.color || 0;
        return index === 0 ? null : (COLORS[index] || COLORS[0]);
    }

    get onAccentColor() {
        return getOnAccentColor(this.accentColor);
    }

    get backgroundStyle() {
        const index = this.props.color || 0;
        if (this.props.data.use_background_gradient) {
            return (GRADIENTS[index] || GRADIENTS[0]);
        }
        return (COLORS[index] || COLORS[0]);
    }
}

DashboardListWidget.template = xml`
    <div class="o_custom_list_view h-100 d-flex flex-column border rounded shadow-sm overflow-hidden"
         t-attf-style="background: {{ this.backgroundStyle }}; {{ this.accentColor ? '--widget-accent: ' + this.accentColor + '; --widget-on-accent: ' + this.onAccentColor + ';' : '' }}">

        <div class="px-4 py-3 d-flex align-items-center justify-content-between"
             style="border-bottom: 1px solid var(--list-border-color);">

            <div class="d-flex align-items-center gap-2 overflow-hidden list-name">
                <h1 class="m-0 fw-semibold text-truncate" style="font-size: 1.3rem;">
                    <t t-esc="props.data.name"/>
                </h1>
                <span class="dashboard-badge dashboard-badge-list rounded-pill px-3 py-2"
                      style="border: 1px solid var(--list-border-color);">
                    Total: <t t-esc="props.data.total_count or 0"/>
                </span>
            </div>

            <div class="list-tools">
                <button class="btn-insight-list" t-on-click.stop="getChartInsight" title="AI Insight">
                    <i t-att-class="state.isGettingInsight ? 'fa fa-spinner fa-spin' : 'fa fa-lightbulb-o'"/>
                </button>
                <button class="btn-edit-list" t-on-click="onEdit">
                    <i class="fa fa-pencil"/>
                </button>
                <button class="btn-del-list" t-on-click="onDelete">
                    <i class="fa fa-trash"/>
                </button>
            </div>

            <div t-if="!props.isPreview" class="download-options">
                <button class="btn-download-json" t-on-click="downloadJson">
                    <i class="fa fa-download"/>
                </button>
            </div>
        </div>

        <div class="o_list_body flex-grow-1">
        <div class="o_list_main table-responsive custom-scrollbar" style="overflow-y: auto;">
            <table class="table mb-0 w-100 align-middle">
                <thead>
                    <tr>
                        <t t-foreach="props.data.fields" t-as="field" t-key="field.name">
                            <th class="sticky-top border-bottom text-uppercase small fw-bold py-2 px-3"
                                style="top: 0; z-index: 10; letter-spacing: 0.5px; font-size: 0.75rem;">
                                <t t-esc="field.label"/>
                            </th>
                        </t>
                    </tr>
                </thead>
                <tbody>
                    <t t-if="props.data.records.length > 0">
                        <t t-if="props.data.is_grouped">
                            <t t-foreach="props.data.records" t-as="group" t-key="group.group_name">

                                <tr class="border-bottom cursor-pointer user-select-none"
                                    t-on-click="() => this.toggleGroup(group.group_name)">
                                    <td t-att-colspan="props.data.fields.length" class="py-2 px-3">
                                        <div class="d-flex align-items-center fw-bold">
                                            <i class="fa me-2 opacity-50"
                                               t-att-class="state.expandedGroups[group.group_name] ? 'fa-caret-down' : 'fa-caret-right'"/>

                                            <span class="me-2"><t t-esc="group.group_name"/></span>
                                            <span class="badge border rounded-pill shadow-sm" style="font-size: 0.7em;">
                                                <t t-esc="group.records.length"/>
                                            </span>
                                        </div>
                                    </td>
                                </tr>

                                <t t-if="state.expandedGroups[group.group_name]">
                                    <tr t-foreach="group.records" t-as="record" t-key="record.id"
                                        t-att-class="'border-bottom ' + (props.data.row_clickable ? 'cursor-pointer' : '')"
                                        style="height: 45px;"
                                        t-on-click="() => this.onRowClick(record)">

                                        <t t-foreach="props.data.fields" t-as="field" t-key="field.name">
                                            <td class="text-truncate px-3" style="max-width: 200px;" t-att-title="record[field.name]">
                                                <span t-att-class="field_index === 0 ? 'ps-3' : ''" class="d-block text-truncate">
                                                    <t t-esc="record[field.name]"/>
                                                </span>
                                            </td>
                                        </t>
                                    </tr>
                                </t>
                            </t>
                        </t>

                        <t t-else="">
                            <tr t-foreach="paginatedRecords" t-as="record" t-key="record.id"
                                t-att-class="'border-bottom ' + (props.data.row_clickable ? 'cursor-pointer' : '')"
                                style="height: 45px;"
                                t-on-click="() => this.onRowClick(record)">

                                <t t-foreach="props.data.fields" t-as="field" t-key="field.name">
                                    <td class="text-truncate px-3" style="max-width: 200px;" t-att-title="record[field.name]">
                                        <span class="d-block text-truncate">
                                            <t t-esc="record[field.name]"/>
                                        </span>
                                    </td>
                                </t>
                            </tr>
                        </t>
                    </t>

                    <t t-else="">
                        <tr>
                            <td t-att-colspan="props.data.fields.length" class="text-center p-5">
                                <div class="text-muted d-flex flex-column align-items-center">
                                    <i class="fa fa-folder-open-o fa-3x mb-3 opacity-50"/>
                                    <span class="fw-medium">No records found</span>
                                </div>
                            </td>
                        </tr>
                    </t>
                </tbody>
            </table>
        </div>

        <div t-if="state.aiInsight"
             class="chart-ai-insight-side-panel o_list_insight_panel shadow-sm animate__animated animate__fadeIn">
            <div class="d-flex align-items-center mb-1">
                <i class="fa fa-magic me-2 small"/>
                <span class="fw-bold extra-small">AI Insight</span>
                <button class="btn-close ms-auto shadow-none small"
                        style="transform: scale(0.6);"
                        t-on-click.stop="() => state.aiInsight = null"/>
            </div>
            <div class="insight-text extra-small">
                <t t-esc="state.aiInsight"/>
            </div>
        </div>
        </div>

        <div t-if="!props.data.is_grouped and totalPages > 1" class="px-3 py-2 border-top d-flex justify-content-between align-items-center flex-shrink-0" style="font-size: 0.85rem;">
            <span class="text-muted">
                Showing <t t-esc="((state.currentPage - 1) * limitPerPage) + 1"/>
                -
                <t t-esc="Math.min(state.currentPage * limitPerPage, props.data.records.length)"/>
                of <t t-esc="props.data.records.length"/>
            </span>

            <div class="btn-group">
                <button class="btn btn-sm btn-outline-secondary border-0"
                        t-att-disabled="isFirstPage"
                        t-on-click="() => this.setPage('prev')">
                    <i class="fa fa-chevron-left"/>
                </button>
                <button class="btn btn-sm btn-outline-secondary border-0 disabled fw-bold" style="color: var(--widget-text-color);">
                    <t t-esc="state.currentPage"/> / <t t-esc="totalPages"/>
                </button>
                <button class="btn btn-sm btn-outline-secondary border-0"
                        t-att-disabled="isLastPage"
                        t-on-click="() => this.setPage('next')">
                    <i class="fa fa-chevron-right"/>
                </button>
            </div>
        </div>
    </div>
`;
