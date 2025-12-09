/** @odoo-module **/

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.order;

        console.log("✅ OrderPaymentValidation.validateOrder TRIGGERED");

        // ✅ ✅ CORRECT TOTAL & PAID VALUES
        const total = order.getTotalWithTax();
        const paid = order.getTotalPaid();
        const remaining = total - paid;

        console.log("TOTAL:", total, "PAID:", paid, "REMAINING:", remaining);

        // ✅ Blackbox Check (unchanged)
        if (this.pos.useBlackBoxBe && this.pos.useBlackBoxBe() && !this.pos.userSessionStatus) {
            this.pos.env.services.dialog.add(AlertDialog, {
                title: _t("POS Error"),
                body: _t(
                    "The government's Fiscal Data Module requires every user to Clock In."
                ),
            });
            throw new Error("Blackbox not clocked in");
        }

        if (!order) {
            return await super.validateOrder(isForceValidate);
        }

        // ✅ Normal orders → default flow
        if (!order.is_partial_payment) {
            return await super.validateOrder(isForceValidate);
        }

        // ✅ Customer restriction
        if (order.getPartner()?.prevent_partial_payment) {
            this.pos.env.services.dialog.add(AlertDialog, {
                title: _t("Partial Payment Not Allowed"),
                body: _t("This customer is not allowed to use Partial Payments."),
            });
            throw new Error("Partial payment blocked");
        }

        // ✅ Invoice rule (only if you still want it)
        if (!order.isToInvoice()) {
            this.pos.env.services.dialog.add(AlertDialog, {
                title: _t("Invoice Required"),
                body: _t("Enable Invoice for Partial Payments."),
            });
            throw new Error("Invoice required");
        }

        // ✅ ✅ FIXED: Real payment validation (NO RANDOM FAIL ANYMORE)
        if (paid <= 0) {
            this.pos.env.services.dialog.add(AlertDialog, {
                title: _t("No Payment"),
                body: _t("Please add a payment before validating."),
            });
            throw new Error("No payment entered");
        }

        return await super.validateOrder(isForceValidate);
    },
});
