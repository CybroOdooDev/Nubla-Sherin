/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/* This widget allows users to select a font style for dashboard tiles. It provides a preview of each style and updates the record with the selected style class. */
export class FontStyleWidget extends Component {
    static template = "multi_dashboard.FontStyleWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.styles = [
            { id: 'tile-style-modern', name: 'Modern', preview: '123' },
            { id: 'tile-style-elegant', name: 'Elegant', preview: '123' },
            { id: 'tile-style-tech', name: 'Tech', preview: '123' },
            { id: 'tile-style-impact', name: 'Bold', preview: '123' },
        ];
    }

    // Retrieves the currently selected font style class from the record, defaulting to "tile-style-modern" if none is set.
    get selectedValue() {
        return this.props.record.data[this.props.name] || "tile-style-modern";
    }

    // Updates the record with the selected font style class when a user selects a style.
    selectStyle(styleClass) {
        this.props.record.update({ [this.props.name]: styleClass });
    }

    // Checks if a given style class is currently selected, used to apply the appropriate styling in the UI.
    isSelected(styleClass) {
        return this.selectedValue === styleClass;
    }
}

// Correct Registration for Odoo 17+
registry.category("fields").add("font_style_selector", {
    component: FontStyleWidget,
    supportedTypes: ["char"],
});
