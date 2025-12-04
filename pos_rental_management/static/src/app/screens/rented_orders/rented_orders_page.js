/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { registry } from "@web/core/registry";

export class RentedProductDetailsScreen extends Component {
    static template = "pos_rental_management.RentedProductDetailsScreen";

    setup() {
        this.pos = usePos();
        this.state = useState({
            filteredOrders: [],  // Initialize with empty array or load data
            searchTerm: ''
        });
        this.loadRentedOrders();
    }

    loadRentedOrders() {
    const model = this.pos.models['rental.product.tenure'];
    console.log(model,"gggggggggggg")

    if (!model) {
        this.state.filteredOrders = [];
        return;
    }

    const records = Array.from(model.records.values());

    this.state.filteredOrders = records.map(record => ({
        id: record.id,
        name: record.name,
        customer: record.partner_id?.[1] || '-',
        product: record.product_id?.[1] || '-',
        tenure: record.tenure || '-',
        date: record.date_start || '-',
        status: 'Rented'
    }));
}



    onSearchOrder(ev) {
        this.state.searchTerm = ev.target.value;
        // Implement filtering logic
        this.state.filteredOrders = this.getAllOrders().filter(order =>
            order.name.toLowerCase().includes(this.state.searchTerm.toLowerCase())
        );
    }

    getAllOrders() {
        // Return full orders list for filtering
        return this.pos.models['rental.product.tenure']?.records || [];
    }

    onClickOrder(order) {
        console.log('Selected order:', order);
    }

    onClickBack() {
        this.pos.navigate("ProductScreen");
    }



    onClickReturnRefund() {
        alert("Return/Refund clicked!");
    }

    onClickClose() {
        this.pos.showScreen("ProductScreen");
    }
}

RentedProductDetailsScreen.props = {
    stateOverride: { type: Object, optional: true },
    reuseSavedUIState: { type: Boolean, optional: true }
};

registry.category("pos_pages").add("RentedProductDetailsScreen", {
    name: "RentedProductDetailsScreen",
    component: RentedProductDetailsScreen,
    route: `/pos/ui/${odoo.pos_config_id}/rentedproduct`,
    params: {},
});
