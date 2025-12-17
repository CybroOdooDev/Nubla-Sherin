/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        const res = super.export_for_printing(...arguments);

        let fields = [];
        try {
            fields = JSON.parse(this.config.selected_product_fields || "[]");
        } catch {
            fields = [];
        }

        res.dynamic_fields = fields;
        const jsLines = this.lines || [];

        res.orderlines = (res.orderlines || []).map((line, index) => {
            const enriched = { ...line };

            const jsLine = jsLines[index];
            const product = jsLine?.product_id;

            fields.forEach(f => enriched[f] = "");

            if (product) {
                fields.forEach(f => {
                    let value = product[f];

                    if (value === undefined || value === null) {
                        value = "";
                    } else if (typeof value === "object") {
                        value = value.display_name || value.name || "";
                    } else {
                        value = String(value);
                    }
                    enriched[f] = value;
                });
            }
            return enriched;
        });

        return res;
    },
});

