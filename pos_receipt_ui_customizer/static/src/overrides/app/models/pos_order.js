/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        const res = super.export_for_printing(...arguments);
        const jsLines = this.lines || [];

        const config = this.config;
        const receiptId = config.receipt_id?.id;
        console.log("RECEIPT ID",receiptId)
        const receipt = this.models["pos.receipt"]?.records.find(r => r.id === receiptId);

        let fields = [];
        try {
            fields = JSON.parse(receipt?.selected_product_fields || "[]");
        } catch (e) {
            console.warn("Failed to parse selected_product_fields", e);
            fields = [];
        }

        fields = Array.isArray(fields) ? fields : [];
        res.dynamic_fields = fields;

        res.orderlines = (res.orderlines || []).map((line, i) => {
    const enriched = { ...line };
    const jsLine = jsLines[i];
    const product = jsLine?.product_id;

    console.log("Processing line:", i);
    console.log("Fields to add:", fields);
    console.log("Product object:", product);

    fields.forEach((fieldName) => {
        enriched[fieldName] = "";
    });

    if (product) {
        fields.forEach((fieldName) => {
            if (fieldName in product && product[fieldName] !== undefined && product[fieldName] !== null) {
                enriched[fieldName] = product[fieldName];
                console.log(`Set ${fieldName} =`, product[fieldName]);
            } else {
                console.log(`Field ${fieldName} not found in product`);
            }
        });
    }

    console.log("Final enriched line:", enriched);
    return enriched;
});

        return res;
    },
});