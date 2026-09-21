/** @odoo-module */

import { NavBar } from "@web/webclient/navbar/navbar";
import { registry } from "@web/core/registry";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef, onMounted, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ensureAppIcon } from "./app_icon_fallback";

patch(NavBar.prototype, {
    // To modify the Navbar properties and functions.
    setup() {
        super.setup()
        const isSidebarHidden = sessionStorage.getItem("isSidebarHidden") === "true";
        this.sidebarRef = useRef("sidebar");
        this.menu_sectionsRef = useRef("menu_sections")
        this.busService = useService("bus_service");
        // Patches the raw, shared menu objects in place - menuService.getApps()
        // always returns the same underlying references, so this also fixes the
        // Home Menu grid (home_menus.js), which reads from the same service.
        this.menuService.getApps().forEach(ensureAppIcon);
        const { apps } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        Object.assign(this.state, {
            activeApp: parseInt(sessionStorage.getItem("activeApp")) || null,
            isSidebarHidden: isSidebarHidden,
        });
        useBus(this.env.bus, "app-selected", (event) => {
            this.onAppClick(event.detail.activeApp);
        });
        // Keep the "hide navbar brand/background on the Home Menu" state in sync
        // with whatever action is actually showing, not just with our own back-arrow
        // click handler - otherwise a hard refresh (or deep link) landing directly on
        // the Home Menu action leaves the navbar solid and the app name visible.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            this.syncHomeMenuBodyClass();
        });
        onMounted(() => {
            this.applySidebarState();
            this.syncHomeMenuBodyClass();
        });
    },

    syncHomeMenuBodyClass() {
        const isHomeMenuActive = this.actionService.currentController?.action?.tag === "nhs_backend_theme.homemenus";
        document.body.classList.toggle("o_home_menu_active", isHomeMenuActive);
        if (isHomeMenuActive) {
            const sidebarElement = this.sidebarRef.el;
            const sectionsElement = this.menu_sectionsRef.el;
            const actionManagerElement = document.querySelector(".o_action_manager");
            sidebarElement?.classList.add("o_hidden");
            sectionsElement?.classList.add("o_hidden");
            actionManagerElement?.style.setProperty("margin-left", "0", "important");
            this.state.isSidebarHidden = true;
            sessionStorage.setItem("isSidebarHidden", "true");
        }
    },

    applySidebarState() {
        const sidebarElement = this.sidebarRef.el;
        const sectionsElement = this.menu_sectionsRef.el;
        if (sidebarElement) {
            const actionManagerElement = document.querySelector(".o_action_manager");
            if (this.state.isSidebarHidden) {
                sidebarElement.classList.add("o_hidden");
                if (sectionsElement) sectionsElement.classList.add("o_hidden");
                actionManagerElement?.style.setProperty("margin-left", "0", "important");
            } else {
                sidebarElement.classList.remove("o_hidden");
                if (sectionsElement) sectionsElement.classList.remove("o_hidden");
                actionManagerElement?.style.setProperty("margin-left", "120px");
            }
        }
    },

    onAppClick(app) {
        const sidebarElement = this.sidebarRef.el; // Access the DOM element
        const sectionsElement = this.menu_sectionsRef.el;
        sidebarElement?.classList.remove("o_hidden"); // Remove the 'o_hidden' class to show the sidebar
        sectionsElement?.classList.remove("o_hidden"); // Remove the 'o_hidden' class to show the sidebar
        this.state.isSidebarHidden = false;
        sessionStorage.setItem("isSidebarHidden", "false");
        this.state.activeApp = app.id;
        sessionStorage.setItem("activeApp", this.state.activeApp);
        document.body.classList.remove("o_home_menu_active");
        // The sidebar overlays the content (position: fixed) instead of pushing it,
        // so the content margin always stays at the collapsed-rail width regardless
        // of whether the sidebar is currently hover-expanded.
        document.querySelector(".o_action_manager")?.style.setProperty("margin-left", "120px");
        this.onNavBarDropdownItemSelection(app);
    },

    async _onClickMenusPanel() {
        // Guard against overlapping clicks (e.g. double-clicking the back arrow):
        // a second call while the first is still resolving would race against it
        // and leave the navbar/sidebar in a half-updated state.
        if (this._menuPanelBusy) {
            return;
        }
        this._menuPanelBusy = true;
        try {
            await this._doClickMenusPanel();
        } finally {
            this._menuPanelBusy = false;
        }
    },

    async _doClickMenusPanel() {
        const sidebarElement = this.sidebarRef.el; // Access the DOM element
        const sectionsElement = this.menu_sectionsRef.el;
        const actionManagerElement = document.querySelector(".o_action_manager");
        const isHomeMenuActive = this.actionService.currentController?.action?.tag === "nhs_backend_theme.homemenus";

        if (isHomeMenuActive) {
            // Already on the Home Menu: go back to whatever was open before it,
            // instead of stacking another Home Menu action on top.
            try {
                await this.actionService.restore();
            } catch {
                // Nothing to go back to (Home Menu was the first thing opened).
                return;
            }
            // actionService.restore() doesn't update the menu service's notion of the
            // "current app", so the top menu tabs would otherwise stay empty after
            // going back. Re-derive it from the restored action, same as Odoo's own
            // webclient bootstrap does on initial load.
            const restoredActionId = this.actionService.currentController?.action?.id;
            const restoredMenu = restoredActionId &&
                this.menuService.getAll().find((m) => m.actionID === restoredActionId);
            if (restoredMenu) {
                this.menuService.setCurrentMenu(restoredMenu.appID);
            }
            sidebarElement?.classList.remove("o_hidden");
            sectionsElement?.classList.remove("o_hidden");
            actionManagerElement?.style.setProperty("margin-left", "120px");
            this.state.isSidebarHidden = false;
            sessionStorage.setItem("isSidebarHidden", "false");
            document.body.classList.remove("o_home_menu_active");
            return;
        }

        sidebarElement?.classList.add("o_hidden"); // Add the 'o_hidden' class to hide the sidebar
        sectionsElement?.classList.add("o_hidden"); // Add the 'o_hidden' class to hide the sidebar
        actionManagerElement?.style.setProperty("margin-left", "0", "important");
        this.state.isSidebarHidden = true;
        sessionStorage.setItem("isSidebarHidden", "true");
        // The navbar's app-name/breadcrumb still reflects whatever app was open
        // before the Home Menu (we deliberately don't touch the menu service's
        // current-app here, so "back" keeps working) - hide it while browsing
        // the app grid so it doesn't look like a leftover page title.
        document.body.classList.add("o_home_menu_active");
        await this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'nhs_backend_theme.homemenus',
            params: {
                apps: this._apps,
            },
        });
    }
})