/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { NhsAppointmentPickerDialog } from "@epic_integration/components/nhs_appointment_picker/nhs_appointment_picker";

class NhsAppointmentTypeListController extends ListController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async createRecord() {
        this.dialog.add(NhsAppointmentPickerDialog, {});
    }
}

const nhsAppointmentTypeListView = {
    ...listView,
    Controller: NhsAppointmentTypeListController,
};

registry.category("views").add("nhs_appointment_type_list", nhsAppointmentTypeListView);
