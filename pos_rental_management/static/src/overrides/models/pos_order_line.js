/** @odoo-module */
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";
patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.is_rental && this.rental_info?.tenure_name) {
            this.rental_tenure_name = this.rental_info.tenure_name;
        }
        else if (this.is_security) {
            this.rental_tenure_name =
                "Security Amount Product (Rental Product with Security)";
        }
        else {
            this.rental_tenure_name = false;
        }
    },

    getDisplayData() {
        const displayData = super.getDisplayData();
        return {
            ...displayData,
            rental_tenure_name: this.rental_tenure_name,
        };
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup();
    }
});
