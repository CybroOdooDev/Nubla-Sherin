/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getDarkMode, onDarkModeChange } from "./dark_mode_manager";

// Root menu xmlid for the Fitness Center app.
const FITNESS_APP_XMLID = "fitness_center_management.menu_fitness_root";

function isInFitnessApp(env) {
    return env.services.menu.getCurrentApp()?.xmlid === FITNESS_APP_XMLID;
}

/**
 * Scope the dark-mode CSS to the Fitness Center app only.
 *
 * The styles are global in the backend asset bundle, so we only toggle
 * the `fitness-dark-mode` class when the current app is Fitness Center.
 */
export const fitnessDarkModeScopeService = {
    dependencies: ["menu"],
    start(env) {
        const apply = () => {
            const enabled = isInFitnessApp(env) && getDarkMode();
            document.body?.classList.toggle("fitness-dark-mode", enabled);
        };

        const onAppChanged = () => apply();
        env.bus.addEventListener("MENUS:APP-CHANGED", onAppChanged);
        const off = onDarkModeChange(() => apply());

        apply();

        return {
            destroy() {
                env.bus.removeEventListener("MENUS:APP-CHANGED", onAppChanged);
                off();
            },
        };
    },
};

registry.category("services").add("fitness_dark_mode_scope", fitnessDarkModeScopeService);

