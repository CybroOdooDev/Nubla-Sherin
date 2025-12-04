/** @odoo-module **/

import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PartnerLine.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    async onClickViewRentalProducts() {
        const partner_id = this.props.partner.id;

        const rented_data = await rpc("/pos/get_rented_products", {
            partner_id,
        });

        let msg = "";

        if (!rented_data.length) {
            msg = "No rented products found for this customer.";
        } else {
            msg = rented_data
                .map(item => `${item.product_name} — Qty: ${item.quantity}`)
                .join("<br>");
        }

        this.dialog.add(AlertDialog, {
            title: "Rented Products",
            body: msg,
        });
    },
});
