/** @odoo-module **/
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {

    setup(vals = {}) {
        super.setup(vals);

        this.rental_info = vals.rental_info || false;
        this.is_security = vals.is_security || false;
        this.main_product_name = vals.main_product_name || "";
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            rental_info: this.rental_info,
            is_security: this.is_security,
            main_product_name: this.main_product_name,
        };
    },
});
