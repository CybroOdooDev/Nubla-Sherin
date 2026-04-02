/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(PaymentScreen.prototype, {
    _getPaymentMethodsForLookup() {
        return this.payment_methods_from_config || [];
    },

    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    },

    getHotelChargePaymentMethod() {
        return this._getPaymentMethodsForLookup().find((m) => {
            const loaded = this.pos.models["pos.payment.method"].get(m.id);
            return (
                m.is_hotel_charge ||
                loaded?.is_hotel_charge
            );
        });
    },

    /** Hotel charge method, else Odoo "Customer Account" (pay_later / no journal). */
    getPayAtCheckoutPaymentMethod() {
        const hotel = this.getHotelChargePaymentMethod();
        if (hotel) {
            return hotel;
        }
        return this._getPaymentMethodsForLookup().find((m) => {
            const loaded = this.pos.models["pos.payment.method"].get(m.id);
            return m.type === "pay_later" || loaded?.type === "pay_later";
        });
    },

    async onClickPayAtCheckout() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }
        if (!order.getBookingId()) {
            this.dialog.add(AlertDialog, {
                title: _t("Please select the Room"),
                body: _t("Select a room booking before using Pay at Checkout."),
            });
            return;
        }

        if (!order.partner_id) {
            this.dialog.add(AlertDialog, {
                title: _t("Customer Required"),
                body: _t("Please select a customer before using Pay at Checkout as an invoice will be created."),
            });
            return;
        }

        // Automatically enable invoicing for this order
        order.setToInvoice(true);

        const method = this.getPayAtCheckoutPaymentMethod();
        if (!method) {
            this.dialog.add(AlertDialog, {
                title: _t("No suitable payment method"),
                body: _t(
                    'Add the standard "Customer Account" payment method (leave Journal empty) to this Point of Sale, or create a method with "Is Hotel Charge" enabled.'
                ),
            });
            return;
        }

        // Add payment line for the remaining amount
        const result = await order.addPaymentline(method);
        if (result.status) {
            const paymentLine = result.data;
            paymentLine.setAmount(order.remainingDue);

            try {
                // Use the standard Odoo 19 validation utility
                const validation = new OrderPaymentValidation({
                    pos: this.pos,
                    orderUuid: order.uuid,
                });
                
                // Finalize the validation (this sets state to 'paid', syncs to server, etc.)
                const success = await validation.finalizeValidation();
                
                if (success) {
                    // Navigate to a new order
                    const newOrder = this.pos.addNewOrder();
                    this.pos.navigateToOrderScreen(newOrder);

                    // Show success message
                    this.dialog.add(AlertDialog, {
                        title: _t("Success"),
                        body: _t("Success: The order has been recorded. You are able to set this as 'no need paying from here'; please settle at checkout."),
                    });
                }
            } catch (error) {
                console.error("Error during Pay at Checkout validation:", error);
                this.notification.add(_t("An error occurred while validating the order."), { type: "danger" });
            }
        }
    },

    async addNewPaymentLine(paymentMethod) {
        const order = this.currentOrder;
        const loaded = paymentMethod?.id
            ? this.pos.models["pos.payment.method"].get(paymentMethod.id)
            : null;
        const isHotelCharge = paymentMethod?.is_hotel_charge || loaded?.is_hotel_charge;
        if (isHotelCharge) {
            if (!order.getBookingId()) {
                this.dialog.add(AlertDialog, {
                    title: _t("Please select the Room"),
                    body: _t("Select a room booking before using Pay at Checkout."),
                });
                return false;
            }
            if (!order.isToInvoice()) {
                const confirmed = await new Promise((resolve) => {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Invoice required"),
                        body: _t(
                            "Enable invoicing for this order to use the hotel charge payment method?"
                        ),
                        confirm: () => {
                            order.setToInvoice(true);
                            resolve(true);
                        },
                        cancel: () => resolve(false),
                    });
                });
                if (!confirmed) {
                    return false;
                }
            }
        }
        return await super.addNewPaymentLine(paymentMethod);
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        const hotel_payments = (order?.payment_ids || []).filter(
            (line) => line.payment_method_id?.is_hotel_charge
        );

        if (hotel_payments.length > 0 && !order.getBookingId()) {
            const confirmed = await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Please select the Room"),
                    body: _t("You need to select a hotel room booking before using Pay at Checkout."),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
            if (!confirmed) {
                return;
            }
            return;
        }

        if (hotel_payments.length > 0 && !order.isToInvoice()) {
            const confirmed = await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Please select the Invoice"),
                    body: _t("You need to select the invoice before using Pay at Checkout."),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
            if (!confirmed) {
                return;
            }
            return;
        }

        return await super.validateOrder(isForceValidate);
    }
});
