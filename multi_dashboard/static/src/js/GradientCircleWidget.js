/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/* This widget allows users to select a gradient from a predefined list.
The selected gradient is stored as a string in the corresponding field of the record.
The widget displays the gradients as circular options, and the selected gradient is highlighted. */
export class GradientCircleWidget extends Component {
    static template = "multi_dashboard.GradientCircleWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.gradients = [
            { id: 1, gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" },
            { id: 2, gradient: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" },
            { id: 3, gradient: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)" },
            { id: 4, gradient: "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)" },
            { id: 5, gradient: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)" },
            { id: 6, gradient: "linear-gradient(135deg, #30cfd0 0%, #330867 100%)" },
            { id: 7, gradient: "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)" },
            { id: 8, gradient: "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)" },
            { id: 9, gradient: "linear-gradient(135deg, #654ea3, #eaafc8)" },
        ];
    }

    // This computed property retrieves the currently selected gradient value from the record's data.
    get selectedValue() {
        return this.props.record.data[this.props.name] || "";
    }

    // This method is called when a user selects a gradient.
    selectGradient(gradient) {
        this.props.record.update({ [this.props.name]: gradient });
    }

    // This method checks if a given gradient is the currently selected one, which is used to apply the appropriate styling in the template.
    isSelected(gradient) {
        return this.selectedValue === gradient;
    }
}

registry.category("fields").add("gradient_circle", {
    component: GradientCircleWidget,
    supportedTypes: ["char"],
});
