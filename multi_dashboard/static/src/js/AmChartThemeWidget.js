/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AmChartThemeWidget extends Component {
    static template = "multi_dashboard.AmChartThemeWidget";
    static props = { ...standardFieldProps };

    setup() {
        // Hardcoded color palettes corresponding to AmCharts themes
        this.themeColors = {
            'default': ['#67b7dc', '#6794dc', '#6771dc', '#8067dc', '#a367dc'],
            'material': ['#2196f3', '#f44336', '#ff9800', '#4caf50', '#00bcd4'],
            'kelly': ['#F2F3F4', '#222222', '#F3C300', '#875692', '#F38400', '#A1CAF1'],
            'dataviz': ['#283250', '#902c2d', '#d5433d', '#f05440'],
            'moonrise': ['#3a1302', '#601205', '#8a2b0d', '#c75e24', '#c79f59'],
            'frozen': ['#bec4f8', '#a5abee', '#6a6dde', '#4d42cf', '#713e8d'],
            'spiritedaway': ['#65738e', '#523b58', '#a43820', '#f07f59', '#f2b46f'],
        };
    }

    /**
     * Handle theme selection
     * @param {String} value - The theme key (e.g., 'material')
     */
    onSelectTheme(value) {
        this.props.record.update({ [this.props.name]: value });
    }

    /**
     * Get the list of selection options from the field definition
     */
    get options() {
        // Retrieve selection options defined in the Python model
        return this.props.record.fields[this.props.name].selection.map(opt => ({
            value: opt[0],
            label: opt[1],
            colors: this.themeColors[opt[0]] || ['#cccccc'] // Fallback color
        }));
    }
}

// Register the widget to be used in views
export const amChartThemeWidget = {
    component: AmChartThemeWidget,
};

registry.category("fields").add("am_chart_theme_widget", amChartThemeWidget);
