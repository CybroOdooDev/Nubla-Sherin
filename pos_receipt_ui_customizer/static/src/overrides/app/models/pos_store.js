///** @odoo-module */
//
//import { PosStore } from "@point_of_sale/app/store/pos_store";
//import { patch } from "@web/core/utils/patch";
//
//patch(PosStore.prototype, {
//    async setup() {
//        await super.setup(...arguments);
//
//        // receipt linked to this POS config
//        const receipt = this.config?.receipt_id;
//        console.log("RECEIPT<<<<<<<<<<<<<1", this)
//        console.log("RECEIPT<<<<<<<<<<<<<2", this.config)
//        console.log("RECEIPT<<<<<<<<<<<<<", receipt)
//
//        if (receipt?.selected_product_fields) {
//            this.config.selected_product_fields =
//                receipt.selected_product_fields;
//        }
//
//        // Load font style from receipt
//        if (receipt?.design_receipt_font_style) {
//            this.config.design_receipt_font_style = receipt.design_receipt_font_style;
//        }
//    },
//});
