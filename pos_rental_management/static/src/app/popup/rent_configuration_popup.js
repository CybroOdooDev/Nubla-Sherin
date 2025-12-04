/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";

export class RentConfigurationPopup extends Component {
    static template = "pos_rental_management.RentConfigurationPopup";
    static props = ["product", "tenure", "close", "confirm"];
    static components = { Dialog };

    setup() {
        this.state = useState({
            count: "",
            start_date: "",
            end_date: "",
            note: "",
        });
    }

    proceed() {
        this.props.confirm({
            tenure: this.props.tenure,
            count: this.state.count,
            start_date: this.state.start_date,
            end_date: this.state.end_date,
            note: this.state.note,
        });
        this.props.close();
    }
}
