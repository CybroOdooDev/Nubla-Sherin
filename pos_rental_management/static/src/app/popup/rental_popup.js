/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

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

    /** List of tenures */
    get tenures() {
        return this.props.product.rental_tenure_ids || [];
    }

    selectTenure(ev) {
        this.state.selectedTenureId = parseInt(ev.currentTarget.dataset.id);

        // highlight selected button
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

        this.props.confirm(selectedTenure);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
