/** @odoo-module **/
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(vals);

        // Capture rental details (data coming from your popup)
        this.rental_info = vals.rental_info || null;   // tenure name + duration + rate
        this.security_label = vals.security_label || null;
    },

    export_for_printing() {
        const data = super.export_for_printing(...arguments);
        data.rental_info = this.rental_info;
        data.security_label = this.security_label;
        return data;
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            rental_info: this.rental_info,
            security_label: this.security_label,
        };
    },
});
