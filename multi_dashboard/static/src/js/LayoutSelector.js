/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/* This component allows users to select a dashboard layout.
It displays a list of available layouts and updates the record with the selected layout.
The selected layout is stored in the record's data under the field name specified in props. */
export class LayoutSelector extends Component {
    static template = "multi_dashboard.LayoutSelector";
    static props = { ...standardFieldProps };

    setup() {
        this.layouts = [
            { id: 'layout_1', name: 'Centered' },
            { id: 'layout_2', name: 'Side-by-Side' },
            { id: 'layout_3', name: 'Corner' },
        ];
    }

    // This computed property returns the currently selected layout based on the record's data.
    get selectedLayout() {
        return this.props.record.data[this.props.name] || 'layout_1';
    }

    // This method updates the record with the selected layout when a user clicks on a layout option.
    selectLayout(layoutId) {
        this.props.record.update({ [this.props.name]: layoutId });
    }
}

registry.category("fields").add("layout_selector", {
    component: LayoutSelector,
});
