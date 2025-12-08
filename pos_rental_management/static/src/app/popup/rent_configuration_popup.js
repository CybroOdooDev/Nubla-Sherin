/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";

export class RentConfigurationPopup extends Component {
    static template = "pos_rental_management.RentConfigurationPopup";
    static props = ["product", "tenure", "close", "confirm"];
    static components = { Dialog };

    setup() {
        this.state = useState({
            count: 1,
            start_date: "",
            end_date: "",
            note: "",
        });
    }

    get securityAmount() {
    return this.props.product?.security_amount || 0;
        }


    get rentalPrice() {

        const tenurePrice = this.props.tenure?.amount || 0;
        const count = parseInt(this.state.count) || 1;

        let days = 1;
        if (this.state.start_date && this.state.end_date) {
            const start = new Date(this.state.start_date);
            const end = new Date(this.state.end_date);
            const diff =
                Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
            days = diff > 0 ? diff : 1;
        }

        return tenurePrice * count * days;
    }

    proceed() {
        this.props.confirm({
            tenure: this.props.tenure,
            count: this.state.count,
            start_date: this.state.start_date,
            end_date: this.state.end_date,
            note: this.state.note,
            total_price: this.rentalPrice,
            security_amount: this.securityAmount,
        });

        this.props.close();
    }
}
