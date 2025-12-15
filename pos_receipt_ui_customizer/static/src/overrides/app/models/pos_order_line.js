/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

            console.log("JSON")

patch(PosOrderline.prototype,

    {
        export_for_printing() {
            const json = super.export_for_printing(...arguments);
            console.log(json,"JSON")

            const product = this.product_id;   //correct

            json.volume = product?.volume || "";
            json.product_name = product?.display_name || "";

            return json;
        },
    }
);