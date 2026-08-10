/** @odoo-module **/
/**
 *  This script runs on every backend page load.
 *  It restores the dark mode preference from localStorage
 *  so dark mode persists across all views (list, form, kanban, etc.)
 */
import { syncDarkModeFromStorage } from "./dark_mode_manager";

function applyDarkModeIfPossible() {
    if (!document.body) {
        return;
    }
    syncDarkModeFromStorage();
}

// During the initial page load, modules can be evaluated before <body> exists.
// Avoid crashing the whole asset bundle: apply as soon as the DOM is ready.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyDarkModeIfPossible, { once: true });
} else {
    applyDarkModeIfPossible();
}
