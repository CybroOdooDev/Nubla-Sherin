/** @odoo-module */
import { Component, onWillStart, useState, useEffect, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { DashboardChart } from "./DashboardChart";
import { DashboardTileWidget } from "./DashboardTileWidget";
import { DashboardTodoWidget } from "./DashboardTodoWidget";
import { DashboardListWidget } from "./DashboardListWidget";
import { DashboardClock } from "./DashboardClock";
import { DashboardProgressBar } from "./DashboardProgressBar";

/**
 * Live Preview Widget for Dashboard Charts
 * Updates preview in real-time as form fields change
 */
export class DashboardChartLivePreview extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: null,
            chartData: [],
            chartResult: [],
            config: {}
        });

        // Load preview on component mount
        onWillStart(async () => {
            await this.loadPreview();
        });

        // Reload preview when props update
        useEffect(
            () => {
                this.loadPreview();
            },
            () => [
                this.props.record.data.name,
                this.props.record.data.chart_type,
                this.props.record.data.model_id,
                this.props.record.data.filter,

                this.props.record.data.measure_aggregation,
                this.props.record.data.measure_field_id,
                this.props.record.data.widget_color,
                this.props.record.data.layout_style,
                this.props.record.data.tile_font_style,
                this.props.record.data.font_color,

                this.props.record.data.todo_ids,
                this.props.record.data.todo_ids?.count,
                this.props.record.data.todo_color,

                this.props.record.data.list_field_ids?.count,
                this.props.record.data.list_group_field_id,
                this.props.record.data.list_sort_field_id,
                this.props.record.data.list_sort_direction,
                this.props.record.data.list_limit,
                this.props.record.data.limit_per_page,
                this.props.record.data.list_row_clickable,

                this.props.record.data.chart_group_field_id,
                this.props.record.data.chart_measure_field_ids?.count,
                this.props.record.data.chart_sub_group_field_id,
                this.props.record.data.am_chart_theme,
                this.props.record.data.chart_orientation,
                this.props.record.data.clock_format,
                this.props.record.data.tz,

                this.props.record.data.progress_target_static,
                this.props.record.data.chart_date_group_by,
                this.props.record.data.tile_icon,
                this.props.record.data.tile_unit_format,
                this.props.record.data.use_background_gradient,
                this.props.record.data.enable_forecast,
                this.props.record.data.forecast_periods,
                this.props.record.data.forecast_method,
                this.props.record.data.forecast_ai_cache_ttl_hours,
                this.props.record.data.forecast_history_periods,
            ]
        );
    }

    // Simple debounce helper
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    // Load preview data based on current form state
    async loadPreview() {
        const recordData = this.props.record?.data;

        this.state.loading = true;
        this.state.error = null;

        try {
            // Map To-do Commands
            const todoCommands = [];
            if (recordData.todo_ids && recordData.todo_ids.records) {
                recordData.todo_ids.records.forEach(todo => {
                    todoCommands.push([0, 0, {
                        name: todo.data.name,
                        is_done: todo.data.is_done,
                        sequence: todo.data.sequence,
                    }]);
                });
            }

            // Map List Field Commands
            const listFieldCommands = [];
            if (recordData.list_field_ids && recordData.list_field_ids.records) {
                recordData.list_field_ids.records.forEach(line => {
                    const fieldId = line.data.field_id ? (Array.isArray(line.data.field_id) ? line.data.field_id[0] : (line.data.field_id.id || line.data.field_id)) : false;
                    if (fieldId) {
                        listFieldCommands.push([0, 0, {
                            field_id: fieldId,
                            sequence: line.data.sequence,
                        }]);
                    }
                });
            }
            const chartFieldCommands = [];
            if (recordData.chart_measure_field_ids && recordData.chart_measure_field_ids.records) {
                recordData.chart_measure_field_ids.records.forEach(line => {
                    const fieldId = line.resId || line.data?.id || (Array.isArray(line.data?.field_id) ? line.data.field_id[0] : line.data?.field_id);
                    if (fieldId) {
                        chartFieldCommands.push([4, fieldId]); // Use command 4 (Link to existing) for Many2many
                    }
                });
            }

            // Build configuration from current form state
            const config = {
                // Basic chart settings
                name: recordData.name,
                chart_type: recordData.chart_type,
                model_id: recordData.model_id ? recordData.model_id.id : false,
                model_name: recordData.model_name,
                filter: recordData.filter || "[]",

                // Tile
                measure_aggregation: recordData.measure_aggregation,
                measure_field_id: recordData.measure_field_id ? recordData.measure_field_id.id : false,
                widget_color: recordData.widget_color,
                layout_style: recordData.layout_style,
                tile_font_style: recordData.tile_font_style,
                font_color: recordData.font_color,
                tile_icon: recordData.tile_icon,
                tile_unit_format: recordData.tile_unit_format,

                // To-Do
                todo_ids: todoCommands,
                todo_color: recordData.todo_color,

                // List
                list_field_ids: listFieldCommands,
                list_group_field_id: recordData.list_group_field_id ? recordData.list_group_field_id.id : false,
                list_sort_field_id: recordData.list_sort_field_id ? recordData.list_sort_field_id.id : false,
                list_sort_direction: recordData.list_sort_direction,
                list_limit: recordData.list_limit,
                limit_per_page: recordData.limit_per_page,
                list_row_clickable: recordData.list_row_clickable,

                // Progress Bar
                progress_target_static: recordData.progress_target_static,
                chart_date_group_by: recordData.chart_date_group_by,

                // Chart
                chart_group_field_id: recordData.chart_group_field_id ? recordData.chart_group_field_id.id : false,
                chart_measure_field_ids: chartFieldCommands,
                chart_sub_group_field_id: recordData.chart_sub_group_field_id ? recordData.chart_sub_group_field_id.id : false,
                chart_orientation: recordData.chart_orientation,
                am_chart_theme: recordData.am_chart_theme,
                enable_forecast: recordData.enable_forecast,
                forecast_periods: recordData.forecast_periods,
                forecast_method: recordData.forecast_method,
                forecast_ai_cache_ttl_hours: recordData.forecast_ai_cache_ttl_hours,
                forecast_history_periods: recordData.forecast_history_periods,
                tz: recordData.tz,
                clock_format: recordData.clock_format,
                use_background_gradient: recordData.use_background_gradient,
            };
            if (!config.chart_type) {
                this.state.chartData = [];
                this.state.config = config;
                this.state.loading = false;
                return;
            }

            const result = await this.orm.call(
                "multi.dashboard.charts",
                "get_preview_data",
                [],
                { config: config }
            );

            this.state.chartData = result.data || result;
            this.state.chartResult = result;

            this.state.config = config;

        } catch (error) {
            this.state.error = error.message || "Failed to load preview";
            this.state.chartData = [];
        } finally {
            this.state.loading = false;
        }
    }
}
DashboardChartLivePreview.template = "multi_dashboard.DashboardChartLivePreview"
DashboardChartLivePreview.components = {
    DashboardChart,
    DashboardTileWidget,
    DashboardTodoWidget,
    DashboardListWidget,
    DashboardClock,
    DashboardProgressBar,
};

// Register as a field widget
registry.category("fields").add("dashboard_chart_live_preview", {
    component: DashboardChartLivePreview,
});
