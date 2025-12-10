
/** @odoo-module **/
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { useRef } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.root = useRef('PartialPayment');
    },
    PartialPaymentButton() {
    const order = this.currentOrder;

    if (!order.getPartner()) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("No partner selected"),
            body: _t("Please select partner."),
        });
        return;
    }

    if (order.remainingDue === 0) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Cannot Validate This Order"),
            body: _t("The amount is fully paid. Disable Partial Payment to validate."),
        });
        return;
    }

    order.is_partial_payment = !order.is_partial_payment;

    this.render();
}


});

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        console.log(this)
        if (!this.order.is_partial_payment) {
            await super.validateOrder(isForceValidate);
        } else {

            if (this.order.getPartner()?.prevent_partial_payment) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Partial Payment Not Allowed"),
                    body: _t("The Customer is not allowed to make Partial Payments."),
                });
                return false;
            }

            if (!this.order.to_invoice) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Cannot Validate This Order"),
                    body: _t("You need to Set Invoice for Validating Partial Payments."),
                });
                return false;
            }

            this.order.is_paid = () => true;
            this.order.is_partial_payment = true;
            console.log("this",this)
            const nextPage = this.nextPage;
            this.pos.navigate(nextPage.page, nextPage.params);
            this.isOrderValid(isForceValidate);
            await this.finalizeValidation();
        }
    }
});
