/** @odoo-module */
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// This component represents a single tile in the dashboard.
export class DashboardTileWidget extends Component {
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            data: this.props.data || {},
        });
    }

    // This method will trigger the download of the chart's data in JSON format.
    downloadJson() {
        this.downloadJsonExport({ chart_id: this.props.data.id });
    }

    // This method will trigger the download of the dashboard's data in JSON format.
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

    // When the edit button is clicked, this method will open the form view of the chart for editing.
    onEdit() {
        const tileId = this.props.data.id;
        if (!tileId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts", // Your model name
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

    // When the delete button is clicked, this method will unlink the chart record and refresh the dashboard.
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

    // Method to handle user click on the tile
    async onTileClick(ev) {
        if (this.props.isPreview) return;
        // Check if the click was on one of the action buttons
        if (ev.target.closest('.btn-edit-tile') || ev.target.closest('.btn-del-tile') || ev.target.closest('.btn-download-json')) {
            return; // let the specific button handler handle it
        }

        console.log('PROPSSSSSSSSS', this.props)
        const modelName = this.props.widget?.model_name;
        if (!modelName) return;

        let domain = [];
        if (this.props.filter) {
            try {
                // If the filter can be evaluated/parsed easily, we would do it here.
                // In a robust implementation, the evaluated domain should come from kwargs.
                // We'll leave it empty to just show all records for now or try to pass it if it's an array.
                 if (typeof this.props.filter === 'object') {
                    domain = this.props.filter;
                 }
            } catch (e) {
                console.warn("Could not parse filter domain", e);
            }
        }

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Records for ${this.props.data.name || 'Tile'}`,
            res_model: modelName,
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
        });
    }
}

DashboardTileWidget.template = xml`
    <div t-attf-class="h-100 w-100 dashboard-tile {{state.data.layout_style}} {{state.data.tile_font_style}}"
         t-attf-style="background: {{state.data.widget_color}}; color: {{state.data.font_color}}; cursor: pointer;"
         t-on-click="onTileClick">

        <div class="tile-tools-overlay">
            <button class="btn-edit-tile" t-on-click="onEdit">
                <i class="fa fa-pencil"/>
            </button>
            <button class="btn-del-tile" t-on-click="onDelete">
                <i class="fa fa-trash"/>
            </button>
        </div>
        <div t-if="!props.isPreview" class="download-options">
            <button class="btn-download-json" t-on-click="downloadJson">
                <i class="fa fa-download"/>
            </button>
        </div>
        <div class="tile-value">
            <t t-esc="state.data.value"/>
        </div>
        <div class="tile-label">
            <t t-esc="state.data.name"/>
        </div>
    </div>
`;
