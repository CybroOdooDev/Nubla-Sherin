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

        if (!product.is_rental) {
            return await super.addProductToOrder(product);
        }

        console.log("RENTAL PRODUCT — OPENING POPUP");

        this.dialog.add(RentalSelectionPopup, {
            product,

            confirm: async (tenure) => {
               console.log("KKKKKKKKKKKKKKk",tenure)
               const tenureRecord = tenure.tenure.raw;

               const tenureName = tenureRecord.name;
               console.log("KKKKKKKKKKKKKKk",tenureName)


                const rentalLine = await this.pos.addLineToCurrentOrder(
                    { product_tmpl_id: product },
                    {
                        is_rental: true,
                        rental_tenure_id: tenureName,
                        rental_info: {
                            tenure_name: tenureName,
                            duration: `${tenure.range_start} - ${tenure.range_end} ${tenure.duration_uom}`,
                            amount: tenure.amount,
                        },
                    }
                );
                rentalLine.setUnitPrice(tenure.total_price);

                rentalLine.is_rented = true;
                rentalLine.rental_tenure_name = tenureName;
                console.log("LINEEEEEEEE,",rentalLine.is_rented)

                const secId = this.pos.config.raw.rental_security_product_id;
                if (!secId) {
                    console.warn("No security product configured.");
                    return;
                }

                const securityProduct = this.pos.models['product.product'].get(secId);
                if (!securityProduct) {
                    console.warn("Security product not found in POS DB.");
                    return;
                }

                const securityLine = await this.pos.addLineToCurrentOrder(
                    { product_tmpl_id: securityProduct },
                    {
                        is_security: true,
                        is_rental: false,
                        rental_tenure_name: false,
                        linked_rental_uuid: rentalLine.id,
                    }
                );
                securityLine.setUnitPrice(tenure.security_amount);
                securityLine.is_security = true;
                securityLine.is_rental = false;
                securityLine.rental_tenure_name = false;


                if (rentalLine && securityLine) {
                    rentalLine.security_line_id = securityLine.id;
                    securityLine.rental_line_id = rentalLine.id;
                }
            },
        });

        return;
    },
});
