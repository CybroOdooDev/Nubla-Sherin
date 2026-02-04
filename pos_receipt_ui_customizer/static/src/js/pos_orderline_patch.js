import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {


    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);
        results.label_voloum = ("CHangiii")
        console.log(results, "Resultt")

        return results;
    },
});
