/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const hasPayments = this.order.payment_ids.length > 0;
        const isRentalOrder = this.order.is_rented === true;
        console.log(this.order)
        console.log("RENTED",isRentalOrder)
        const isPartialAllowed = this.pos.config.allow_partial_payment;

        console.log("VALIDATION CHECK →", {
            is_rented: isRentalOrder,
            isPaid: this.order.isPaid(),
            hasPayments: hasPayments,
        });

        if (!hasPayments) {
            this.pos.notification.add(_t("Please enter at least one payment."));
            return false;
        }

        if (isPartialAllowed && isRentalOrder && !this.order.isPaid()) {
            console.log("PARTIAL PAYMENT ALLOWED (RENTAL ONLY)");
            this.order.is_partial_payment = true;
            return true;
        }

        if (!this.order.isPaid()) {
            console.log("FULL PAYMENT REQUIRED (NON-RENTAL)");
            return false;
        }

        return true;
    },
});
