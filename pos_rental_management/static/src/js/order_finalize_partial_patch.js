/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(OrderPaymentValidation.prototype, {
    async finalizeValidation() {

        if (this.order.isPaidWithCash() || this.order.getChange()) {
            this.pos.hardwareProxy.openCashbox();
        }

        this.order.date_order = serializeDateTime(luxon.DateTime.now());

        const toRemove = [];
        for (const line of this.paymentLines) {
            if (!line.amount || line.amount === 0) {
                toRemove.push(line);
            }
        }
        for (const line of toRemove) {
            this.order.removePaymentline(line);
        }

        const total = this.order.getTotalWithTax();
        console.log("TOTAL",total)
        const paid = this.order.getTotalPaid();
                console.log("TOTAL",paid)

        const due = total - paid;
                console.log("TOTAL",due)


        this.order.is_partial_payment = paid < total;
        console.log(this.order.is_partial_payment)
        this.order.partial_paid_amount = paid;
        console.log("LL",this.order.partial_paid_amount)
        this.order.due_amount = due;

        if (paid < total) {
            this.order.state = "partial";
        } else {
            this.order.state = "paid";
        }

        this.pos.addPendingOrder([this.order.id]);

        return await super.finalizeValidation();
    },
});
