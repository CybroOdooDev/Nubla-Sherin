/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    setup() {
        super.setup(...arguments);
        this.is_partial_payment = this.is_partial_payment || false;
    },

    set_order_suggestion(suggestion) {
        this.is_partial_payment = suggestion;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.is_partial_payment = this.is_partial_payment;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.is_partial_payment = json.is_partial_payment || false;
    },
});

