/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class RentedOrdersPage extends Component {
    static template = "pos_rental_management.RentedOrdersPage";

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");

        this.state = useState({
            orders: this.props.orders || []
        });

        onMounted(() => {
            console.log("RentedOrdersPage mounted", this.state.orders);
        });
    }

    back() {
        this.pos.bus.trigger("show-screen", { name: "ProductScreen" });
    }
}

registry.category("pos_pages").add("RentedOrdersPage", {
    name: "RentedOrdersPage",
    component: RentedOrdersPage,
    route: `/pos/ui/${odoo.pos_config_id}/rented_orders`,
});
