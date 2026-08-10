/** @odoo-module **/

const STORAGE_KEY = "fitness_dark_mode";
const EVENT_NAME = "fitness-dark-mode-changed";

export function getDarkMode() {
    return localStorage.getItem(STORAGE_KEY) === "true";
}

export function syncDarkModeFromStorage() {
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { enabled: getDarkMode() } }));
}

export function setDarkMode(enabled) {
    localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { enabled } }));
}

/**
 * Subscribe to dark mode changes triggered by setDarkMode().
 * Returns an unsubscribe function.
 */
export function onDarkModeChange(callback) {
    const handler = (ev) => callback(Boolean(ev.detail?.enabled));
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
}
