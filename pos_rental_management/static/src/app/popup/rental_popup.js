/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { RentConfigurationPopup } from "@pos_rental_management/app/popup/rent_configuration_popup";


export class RentalSelectionPopup extends Component {
    static template = "pos_rental_management.RentalSelectionPopup";
    static props = ["product", "close", "confirm"];
    static components = { Dialog };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            selectedTenureId: null,
        });
    }

    get dialogTitle() {
        return _t("Select rental tenure for %s", this.props.product.name);
    }

    get tenures() {
        return this.props.product.rental_tenure_ids || [];
        console.log("dgssssssssssss",this.props.product.rental_tenure_ids)
    }

    selectTenure(ev) {
        this.state.selectedTenureId = parseInt(ev.currentTarget.dataset.id);

        console.log(ev,"dddd")

        document.querySelectorAll(".o_rental_tenure_btn").forEach((btn) => {
            btn.classList.replace("btn-primary", "btn-secondary");
        });

        ev.currentTarget.classList.replace("btn-secondary", "btn-primary");
    }

    confirmSelection() {
        if (!this.state.selectedTenureId) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("Please select a rental tenure."),
            });
            return;
        }

        const selectedTenure = this.tenures.find(
            (t) => t.id === this.state.selectedTenureId
        );
        this.props.close();
        this.dialog.add(RentConfigurationPopup, {
            product: this.props.product,
            tenure: selectedTenure,
            close: this.props.close,
            confirm: this.props.confirm,
        });
    }

    cancel() {
        this.props.close();
    }
}
