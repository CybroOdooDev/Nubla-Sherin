/** @odoo-module **/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
console.log("gddddddddd")
patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        console.log(this.data.models)
        const posOrderModel = this.models["pos.order"];
        console.log("",posOrderModel)
        const allOrders = Array.from(posOrderModel.records.values());
        console.log("Total orders loaded in POS:", allOrders.length);
        console.log("First 5:", allOrders.slice(0, 5));
    },
});
