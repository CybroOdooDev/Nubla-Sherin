/** @odoo-module **/
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(DropdownItem.prototype, {
    onClick(ev) {
        super.onClick(ev);
        if (ev.target.classList.contains('o_app')) {
            let app = { 'appId': ev.target.dataset.section };
            rpc('/theme_studio/add_recent_app', {
                method: 'call',
                args: [app]
            });
        }
    }
});
