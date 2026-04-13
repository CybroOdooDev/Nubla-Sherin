/** @odoo-module **/

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { getDarkMode, onDarkModeChange, setDarkMode } from "./dark_mode_manager";

const FITNESS_APP_XMLID = "fitness_center_management.menu_fitness_root";

export class DarkModeSystray extends Component {
    static template = "fitness_center_management.DarkModeSystray";

    setup() {
        const savedDark = getDarkMode();
        this.state = useState({
            darkMode: savedDark,
        });

        const off = onDarkModeChange((enabled) => {
            this.state.darkMode = enabled;
        });
        onWillUnmount(() => off());
    }

    toggleDarkMode() {
        setDarkMode(!this.state.darkMode);
    }
}

export const systrayItem = {
    Component: DarkModeSystray,
    isDisplayed: (env) => env.services.menu.getCurrentApp()?.xmlid === FITNESS_APP_XMLID,
};

registry.category("systray").add("fitness_center.DarkModeSystray", systrayItem, { sequence: 10 });
