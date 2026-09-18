/** @odoo-module */

import { NavBar } from "@web/webclient/navbar/navbar";
import { registry } from "@web/core/registry";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef, onMounted, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(NavBar.prototype, {
    // To modify the Navbar properties and functions.
    setup() {
        super.setup()
        const isSidebarHidden = sessionStorage.getItem("isSidebarHidden") === "true";
        this.sidebarRef = useRef("sidebar");
        this.menu_sectionsRef = useRef("menu_sections")
        this.busService = useService("bus_service");
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
            this.setupSidebarHoverSpacing();
        });
    },

    setupSidebarHoverSpacing() {
        const sidebarElement = this.sidebarRef.el;
        if (!sidebarElement) {
            return;
        }
        const actionManagerElement = document.querySelector(".o_action_manager");
        // The sidebar's expanded width depends on each item's label length (short
        // labels like "Apps" barely grow, long ones like "Trust Management" grow
        // a lot), so a fixed margin-left guess either clips long labels or leaves
        // a big gap for short ones. Measure the sidebar's true expanded width
        // instantly - by briefly turning off its transition, forcing a reflow, then
        // restoring it, all within this single synchronous handler so the browser
        // never actually paints the untransitioned state - and apply the matching
        // margin right away, so the content shifts in sync with the sidebar's own
        // expand animation instead of lagging behind it.
        sidebarElement.addEventListener("mouseenter", () => {
            if (this.state.isSidebarHidden) {
                return;
            }
            this.applyExpandedSidebarMargin();
        });
        sidebarElement.addEventListener("mouseleave", () => {
            if (this.state.isSidebarHidden) {
                return;
            }
            actionManagerElement?.style.setProperty("margin-left", "98px");
        });
    },

    applyExpandedSidebarMargin() {
        const sidebarElement = this.sidebarRef.el;
        const actionManagerElement = document.querySelector(".o_action_manager");
        if (!sidebarElement || !actionManagerElement) {
            return;
        }
        sidebarElement.classList.add("o_measuring");
        void sidebarElement.offsetWidth; // force a synchronous reflow at full width
        const width = sidebarElement.getBoundingClientRect().width;
        sidebarElement.classList.remove("o_measuring");
        actionManagerElement.style.setProperty("margin-left", `${Math.ceil(width) + 20}px`);
    },

    syncHomeMenuBodyClass() {
        const isHomeMenuActive = this.actionService.currentController?.action?.tag === "theme_nhs.homemenus";
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
                sectionsElement.classList.add("o_hidden");
                actionManagerElement?.style.setProperty("margin-left", "0", "important");
            } else {
                sidebarElement.classList.remove("o_hidden");
                sectionsElement.classList.remove("o_hidden");
                actionManagerElement?.style.setProperty("margin-left", "98px");
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
        // Clicking an app happens with the mouse over the sidebar, so it's still
        // visually expanded via :hover at this point. Match the content margin to
        // that expanded state instead of always snapping back to the collapsed
        // baseline underneath it - otherwise switching apps without the mouse
        // leaving the sidebar first leaves the content clipped behind it.
        if (sidebarElement && sidebarElement.matches(":hover")) {
            this.applyExpandedSidebarMargin();
        } else {
            document.querySelector(".o_action_manager")?.style.setProperty("margin-left", "98px");
        }
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
        const isHomeMenuActive = this.actionService.currentController?.action?.tag === "theme_nhs.homemenus";

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
            actionManagerElement?.style.setProperty("margin-left", "98px");
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
            tag: 'theme_nhs.homemenus',
            params: {
                apps: this._apps,
            },
        });
    }
})