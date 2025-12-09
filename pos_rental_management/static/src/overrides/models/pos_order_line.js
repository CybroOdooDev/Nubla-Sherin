/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get rentalTenureName() {
        if (this.is_rental && this.rental_info?.tenure_name) {

            return this.rental_info.tenure_name;
        }
        else if (this.is_security) {
            return "Security Amount Product (Rental Product with Security)";
        }
        return false;
    },

    getDisplayData() {
        const displayData = super.getDisplayData();
        return {
            ...displayData,
            rental_tenure_name: this.rentalTenureName,
        };
    },
});
