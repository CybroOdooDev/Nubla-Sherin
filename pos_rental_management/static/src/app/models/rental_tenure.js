/** @odoo-module **/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
console.log("gddddddddd")
patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        console.log(this.data.models)
        const tenureModel = this.models["rental.product.tenure"];
        console.log(tenureModel)
    },
});
