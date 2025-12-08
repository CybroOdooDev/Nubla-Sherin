/** @odoo-module **/

import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { useService } from "@web/core/utils/hooks";

patch(PartnerLine.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    onClickViewRentalProducts() {
        const partner = this.props.partner;

        if (!partner) {
            this.notification.add("Please select a customer first.", { type: "warning" });
            return;
        }

        console.log("Opening rented orders popup for:", partner.id, partner.name);

        this.dialog.add(SelectCreateDialog, {
            title: `Rented POS Orders - ${partner.name}`,
            resModel: "pos.order",
            noCreate: true,
            multiSelect: false,

            domain: [
                ["partner_id", "=", partner.id],
                ["state", "in", ["paid", "done", "invoiced"]],
            ],

            onSelected: (orderIds) => {
                const order_id = orderIds[0];
                console.log("Selected rental order:", order_id);

                this.pos.navigate("CustomerRentedOrdersScreen", {
                    stateOverride: {
                        partner_id: partner.id,
                        partner_name: partner.name,
                        order_id: order_id,
                    },
                });
            },
        });
    },
});
