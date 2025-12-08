/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";

export class RefundReturnPopup extends Component {
    static template = "pos_rental_management.RefundReturnPopup";
    static props = ["default_security", "close", "confirm"];
    static components = { Dialog };

    setup() {
        this.state = useState({
            refund_security_amount: this.props.default_security || 0,
            extra_refund_amount: 0,
            deduction_amount: 0,
        });
    }

    proceed() {
        this.props.confirm({
            refund_security_amount: this.state.refund_security_amount,
            extra_refund_amount: this.state.extra_refund_amount,
            deduction_amount: this.state.deduction_amount,
        });
        this.props.close();
    }


}
