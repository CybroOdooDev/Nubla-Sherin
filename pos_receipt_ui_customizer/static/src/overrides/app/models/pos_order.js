/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

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


        const qrText = this.buildReceiptText();

        res.qr_src = qrCodeSrc(qrText);
        console.log("Qr code src ",res.qr_src)

        const relativeQr = qrCodeSrc(qrText);
        res.qr_src = new URL(relativeQr, window.location.origin).href;
        return res;
    },

//    buildMinimalReceiptText() {
//        const company = this.pos.company || {};
//        const receipt = this.export_for_printing();
//
//        const orderName = this.name || "";
//        const date = receipt.date || "";
//        const seller =
//            company.name +
//            (company.city ? ` (${company.city})` : "");
//
//        const vat = company.vat || "N/A";
//
//        const amountBeforeTax = (
//            receipt.total_without_tax || 0
//        ).toFixed(2);
//
//        const vatAmount = (
//            receipt.amount_tax || 0
//        ).toFixed(2);
//
//        return (
//            `# : ${orderName}\n` +
//            `Date : ${date}\n` +
//            `Seller : ${seller}\n` +
//            `VAT : ${vat}\n` +
//            `Amount Before Tax : ${amountBeforeTax} $\n` +
//            `Amount VAT : ${vatAmount} $`
//        );
//    },

    buildReceiptText() {
        const lines = this.get_orderlines()
            .map(line => {
                const product = line.product || line.product_id;
                if (!product) return null;

                const name = product.display_name || product.name || "Item";
                const qty = line.get_quantity();
                const price = line.get_unit_price();

                return `${name}: ${qty} x ${price.toFixed(2)}`;
            })
            .filter(Boolean)
            .join("\n");

        return (
            `Order: ${this.name}\n` +
            `Date: ${this.date_order}\n\n` +
            `${lines}\n\n` +
            `Total: ${this.get_total_with_tax().toFixed(2)}`
        );
    },
});





//import { PosOrder } from "@point_of_sale/app/models/pos_order";
//import { patch } from "@web/core/utils/patch";
//
//patch(PosOrder.prototype, {
//    export_for_printing() {
//        const res = super.export_for_printing(...arguments);
//
//        let fields = [];
//        try {
//            fields = JSON.parse(this.config.selected_product_fields || "[]");
//            console.log("FIELDS",fields)
//        } catch {
//            fields = [];
//        }
//
//        res.dynamic_fields = fields;
//        const jsLines = this.lines || [];
//
//        res.orderlines = (res.orderlines || []).map((line, index) => {
//            const enriched = { ...line };
//
//            const jsLine = jsLines[index];
//            const product = jsLine?.product_id;
//
//            fields.forEach(f => enriched[f] = "");
//
//            if (product) {
//                fields.forEach(f => {
//                    let value = product[f];
//
//                    if (value === undefined || value === null) {
//                        value = "";
//                    } else if (typeof value === "object") {
//                        value = value.display_name || value.name || "";
//                    } else {
//                        value = String(value);
//                    }
//                    enriched[f] = value;
//                });
//            }
//            return enriched;
//        });
//
//        return res;
//    },
//});

