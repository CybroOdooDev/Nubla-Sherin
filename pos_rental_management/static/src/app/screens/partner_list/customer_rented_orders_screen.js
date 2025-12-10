/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomerRentedOrdersScreen extends Component {
    static template = "pos_rental_management.CustomerRentedOrdersScreen";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");

        const state = this.props.stateOverride || {};

        this.state = useState({
            partner_id: state.partner_id,
            partner_name: state.partner_name,
            order_id: state.order_id,
            orderData: null,
            loading: true,
        });

        console.log("Screen opened with:", {
            partner_id: state.partner_id,
            partner_name: state.partner_name,
            order_id: state.order_id,
        });

        onWillStart(async () => {
            await this.loadOrderDetails();
        });
    }

    async loadOrderDetails() {
        if (!this.state.order_id) {
            this.notification.add("No order selected", { type: "warning" });
            this.state.loading = false;
            return;
        }

        try {
            const orderData = await this.orm.searchRead(
                "pos.order",
                [["id", "=", this.state.order_id]],
                [
                    "name",
                    "partner_id",
                    "date_order",
                    "amount_total",
                    "amount_tax",
                    "state",
                    "session_id",
                    "user_id",
                    "lines",
                ],
                { limit: 1 }
            );

            if (orderData && orderData.length > 0) {
                const order = orderData[0];

                // Fetch order lines
                const lines = await this.orm.searchRead(
                    "pos.order.line",
                    [["order_id", "=", this.state.order_id]],
                    [
                        "product_id",
                        "qty",
                        "price_unit",
                        "price_subtotal",
                        "price_subtotal_incl",
                        "discount",
                        "full_product_name",
                    ]
                );

                this.state.orderData = {
                    ...order,
                    lines: lines,
                };
            } else {
                this.notification.add("Order not found", { type: "danger" });
            }
        } catch (error) {
            console.error("Error loading order details:", error);
            this.notification.add("Failed to load order details", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    back() {
        this.pos.navigate("ProductScreen");
    }

    formatDate(dateString) {
        if (!dateString) return "";
        const date = new Date(dateString);
        return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    }

    formatCurrency(amount) {
        if (!amount) return "0.00";
        return amount.toFixed(2);
    }
}

registry.category("pos_pages").add("CustomerRentedOrdersScreen", {
    name: "CustomerRentedOrdersScreen",
    component: CustomerRentedOrdersScreen,
    route: `/pos/ui/${odoo.pos_config_id}/customer-rented-orders`,
    params: {},
});