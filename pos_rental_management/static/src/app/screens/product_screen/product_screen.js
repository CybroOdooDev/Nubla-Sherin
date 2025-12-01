/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RentalSelectionPopup } from "@pos_rental_management/app/popup/rental_popup";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    async addProductToOrder(product) {
        console.log("PRODUCT CLICKED:", product.name);

        // ✔ If not rental → default POS behavior
        if (!product.is_rental) {
            return await super.addProductToOrder(product);
        }

        // ✔ If rental → show your popup
        console.log("RENTAL PRODUCT — OPENING POPUP");

        this.dialog.add(RentalSelectionPopup, {
            product,

            confirm: async (tenure) => {
                console.log("SELECTED TENURE:", tenure);

                // Add order line with tenure info
                await this.pos.addLineToCurrentOrder(
                    { product_tmpl_id: product },
                    { rental_tenure: tenure }
                );
            },
        });

        // 🚫 Block default add behavior
        return;
    },
});
