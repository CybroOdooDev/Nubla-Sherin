/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { useRef } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.root = useRef("PartialPayment");
    },

    PartialPaymentButton() {
    const order = this.currentOrder;
    console.log("PARTIAL BUTTON CLICKED", order);

    if (!order.getPartner()) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("No Customer Selected"),
            body: _t("Please select a customer to enable Partial Payment."),
        });
        return;
    }

    order.is_partial_payment = !order.is_partial_payment;
    console.log("PARTIAL STATE:", order.is_partial_payment);

    const hasPayments = order.payment_ids.length > 0;

    if (order.is_partial_payment && !hasPayments) {
        const defaultMethod =
            this.pos.payment_methods.find(pm => pm.is_cash_count) ||
            this.pos.payment_methods[0];

        if (!defaultMethod) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("No Payment Method"),
                body: _t("No payment method configured."),
            });
            order.is_partial_payment = false;
            return;
        }

        order.addPaymentline(defaultMethod);
        const line = order.getSelectedPaymentline();

        line.setAmount(1);

        console.log("AUTO PAYMENT LINE + AMOUNT SET");
    }

    if (!order.is_partial_payment && hasPayments) {
        order.payment_ids.forEach(line => order.removePaymentline(line));
        console.log("PAYMENT LINES CLEARED");
    }

    if (this.root.el) {
        this.root.el.classList.toggle("highlight", order.is_partial_payment);
        this.root.el.classList.toggle("active", order.is_partial_payment);
    }
},


});
