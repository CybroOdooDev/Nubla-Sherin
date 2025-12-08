/** @odoo-module **/

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderPaymentValidation.prototype, {

    async validateOrder(isForceValidate = false) {
        const order = this.pos.getOrder();

        if (!order) {
            console.error("❌ No active order");
            return false;
        }

        const remaining = order.getDue();
        const total = order.getTotalDue();
        const paid = total - remaining;
        const allowPartial = this.pos.config.allow_partial_payment;

        console.log("TOTAL:", total);
        console.log("PAID:", paid);
        console.log("REMAINING:", remaining);
        console.log("ALLOW PARTIAL:", allowPartial);

        // ❌ Block when partial disabled
        if (!allowPartial && remaining > 0) {
            await this.popup.add(AlertDialog, {
                title: "Partial Payment Disabled",
                body: "You must collect the full amount before validating.",
            });
            return false;   // ❌ STOP VALIDATION
        }

        // ✅ ✅ ✅ PARTIAL PAYMENT → JUST SAY "VALID"
        if (allowPartial && paid > 0 && remaining > 0) {
            order.rental_paid_amount = paid;
            order.rental_due_amount = remaining;

            console.log("✅ PARTIAL PAYMENT ACCEPTED → RETURN TRUE ONLY");

            // ✅ CRITICAL: DO NOT call super here
            return true;
        }

        // ✅ Full payment → normal validation
        return await super.validateOrder(isForceValidate);
    }

});
