/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class NhsAppointmentPickerDialog extends Component {
    static template = "epic_integration.NhsAppointmentPickerDialog";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ templates: {}, loading: true });

        onWillStart(async () => {
            this.state.templates = await this.orm.call(
                "appointment.type",
                "get_nhs_appointment_type_templates_data",
                []
            );
            this.state.loading = false;
        });
    }

    async onTemplateClick(templateData) {
        const action = await this.orm.call(
            "appointment.type",
            "action_setup_nhs_appointment_type_template",
            [templateData.template_key]
        );
        this.props.close();
        this.action.doAction(action);
    }
}
