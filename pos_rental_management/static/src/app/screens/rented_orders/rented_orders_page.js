/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { RefundReturnPopup } from "@pos_rental_management/js/refund_return_popup";

export class RentedProductDetailsScreen extends Component {
    static template = "pos_rental_management.RentedProductDetailsScreen";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");

        this.state = useState({
            filteredOrders: [],
            searchTerm: '',
            isLoading: true,
            selectedOrder: null,
        });

        onMounted(async () => {
            await this.loadRentedOrders();
        });
    }

    async loadRentedOrders() {
        try {
            this.state.isLoading = true;

            const orders = await this.orm.searchRead(
                "pos.order",
                [['is_rented', '=', true], ['state', '!=', 'cancel']],
                ['name', 'partner_id', 'date_order', 'amount_total']
            );

            const orderIds = orders.map(o => o.id);

            const orderLines = await this.orm.searchRead(
                "pos.order.line",
                [['order_id', 'in', orderIds]],
                ['order_id', 'product_id', 'price_unit', 'qty', 'full_product_name']
            );

            const productIds = [...new Set(orderLines.map(l => l.product_id?.[0]).filter(Boolean))];

            const products = await this.orm.searchRead(
                "product.product",
                [['id', 'in', productIds]],
                ['id', 'product_tmpl_id', 'display_name', 'name']
            );

            const productToTemplate = {};
            const productIdToName = {};

            products.forEach(p => {
                productToTemplate[p.id] = p.product_tmpl_id?.[0];
                productIdToName[p.id] = p.display_name || p.name || p.product_tmpl_id?.[1] || "Unknown Product";
            });

            const tmplIds = [...new Set(products.map(p => p.product_tmpl_id?.[0]).filter(Boolean))];

            // STEP 5: Load product.template including security fields
            const productTemplates = await this.orm.searchRead(
                "product.template",
                [['id', 'in', tmplIds]],
                ['id', 'name', 'is_security_required', 'security_amount']
            );

            const tmplIdToName = {};
            const tmplIdToSecurity = {};

            productTemplates.forEach(t => {
                tmplIdToName[t.id] = t.name;
                tmplIdToSecurity[t.id] = {
                    security_amount: t.security_amount || 0,
                    is_security_required: t.is_security_required || false,
                };
            });

            // STEP 6: Load tenures
            const tenures = await this.orm.searchRead(
                "rental.product.tenure",
                [['product_tmpl_id', 'in', tmplIds]],
                ['name', 'duration_uom', 'range_start', 'range_end', 'amount', 'product_tmpl_id']
            );

            const tmplToTenure = {};

            tenures.forEach(t => {
                const tmplId = t.product_tmpl_id?.[0];

                if (!tmplToTenure[tmplId]) {
                    tmplToTenure[tmplId] = [];
                }

                tmplToTenure[tmplId].push({
                    id: t.id,
                    name: t.name,
                    duration_uom: t.duration_uom,
                    range_start: t.range_start,
                    range_end: t.range_end,
                    amount: t.amount,
                    product_name: tmplIdToName[tmplId] || "Unknown",
                });
            });


            this.state.filteredOrders = orders.map(order => {
                const lines = orderLines.filter(l => l.order_id?.[0] === order.id);

                // Build product names
                const productNames = lines.map(l => {
                    const productId = l.product_id?.[0];
                    return productIdToName[productId] || l.full_product_name || "Unknown Product";
                }).join(", ");

                // Collect tenure list
                const tenureList = [];
                lines.forEach(line => {
                    const productId = line.product_id?.[0];
                    const tmplId = productToTemplate[productId];

                    if (tmplToTenure[tmplId]) {
                        tenureList.push(...tmplToTenure[tmplId]);
                    }
                });

                const uniqueTenures = tenureList.filter(
                    (tenure, index, self) => index === self.findIndex(t => t.id === tenure.id)
                );

                // SECURITY AMOUNT (from first product line)
                let security_amount = 0;
                if (lines.length > 0) {
                    const productId = lines[0].product_id?.[0];
                    const tmplId = productToTemplate[productId];

                    if (tmplId && tmplIdToSecurity[tmplId]) {
                        security_amount = tmplIdToSecurity[tmplId].security_amount;
                    }
                }

                return {
                    id: order.id,
                    order_ref: order.name,
                    customer: order.partner_id?.[1] || "-",
                    date: order.date_order || "-",
                    amount: order.amount_total,
                    status: "Rented",
                    products: productNames || "No Products",
                    tenures: uniqueTenures,
                    price_unit: lines.length ? lines[0].price_unit : 0,
                    security_amount: security_amount,
                    tenure_name: uniqueTenures.length ? uniqueTenures[0].name : "-",
                };
            });

            // Default selection
            if (this.state.filteredOrders.length > 0) {
                this.state.selectedOrder = this.state.filteredOrders[0];
            }

            console.log("FINAL MERGED RESULT:", this.state.filteredOrders);

        } catch (error) {
            console.error("Error loading rented orders:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async onSearchOrder(ev) {
        const value = ev.target.value.toLowerCase();
        this.state.searchTerm = value;

        if (!value) {
            await this.loadRentedOrders();
            return;
        }

        if (!this.originalOrders) {
            this.originalOrders = [...this.state.filteredOrders];
        }

        this.state.filteredOrders = this.originalOrders.filter(order =>
            order.order_ref.toLowerCase().includes(value) ||
            order.customer.toLowerCase().includes(value) ||
            order.products.toLowerCase().includes(value)
        );
    }

    onSelectOrder(order) {
        this.state.selectedOrder = order;
        console.log("Selected Order:", order);
    }


    onClickBack() {
        this.pos.navigate("ProductScreen");
    }

    async onClickReturnRefund() {
    if (!this.state.selectedOrder) {
        console.warn("No order selected!");
        return;
    }

    const selectedOrder = this.state.selectedOrder;

    this.env.services.dialog.add(RefundReturnPopup, {
        default_security: selectedOrder.security_amount,

        confirm: async (vals) => {
            console.log(" Refund Values:", vals);
            await this._openRefundOrder(selectedOrder, vals);
        },
    });
}


async _openRefundOrder(orderData, vals) {
    const pos = this.pos;
    const orm = this.orm;



    const refundOrder = pos.createNewOrder();
    pos.setOrder(refundOrder);

    refundOrder.is_rental_return = true;
    refundOrder.origin_rental_order_id = orderData.id;



    const lines = await orm.searchRead(
        "pos.order.line",
        [["order_id", "=", orderData.id]],
        ["product_id", "qty", "price_unit"]
    );



    if (!lines.length) {

        return;
    }

    let rentalProduct = null;

    for (const line of lines) {
        const productId = line.product_id?.[0];
        if (!productId) continue;

        const product = pos.models["product.product"].get(productId);
        if (!product) continue;



        if (product.is_rental) {
            rentalProduct = product;
        }
    }



    if (rentalProduct) {
        const rentalLine = await pos.addLineToCurrentOrder(
            { product_tmpl_id: rentalProduct },
            { is_refund: true, is_rental: true }
        );

        rentalLine.setQuantity(-1);
        rentalLine.setUnitPrice(0);

    }

    const secId = pos.config.raw.rental_security_product_id;
    let securityProduct = null;

    if (secId) {
        securityProduct = pos.models["product.product"].get(secId);
    }


    if (securityProduct && vals.refund_security_amount > 0) {
        const securityLine = await pos.addLineToCurrentOrder(
            { product_tmpl_id: securityProduct },
            {
                is_refund: true,
                is_security_refund: true,
                is_security: true,
            }
        );

        securityLine.setQuantity(1);
        securityLine.setUnitPrice(-Math.abs(vals.refund_security_amount));

    }

    pos.navigate("ProductScreen");
}

}


registry.category("pos_pages").add("RentedProductDetailsScreen", {
    name: "RentedProductDetailsScreen",
    component: RentedProductDetailsScreen,
    route: `/pos/ui/${odoo.pos_config_id}/rentedproduct`,
});
