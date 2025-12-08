/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate = false) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: this.currentOrder.uuid,
        });

        const isValid = await validation.validateOrder(isForceValidate);

        console.log("PAYMENT VALID RESULT:", isValid);

        if (isValid) {
            await super.validateOrder(true);
            this.pos.navigate("ReceiptScreen", {
                orderUuid: this.currentOrder.uuid,
            });
        }
    }

});
