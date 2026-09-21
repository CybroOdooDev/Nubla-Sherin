/** @odoo-module */

import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ensureAppIcon } from "./app_icon_fallback";

export class HomeMenus extends Component {
    static template = "nhs_backend_theme.home_menus";
    setup() {
        this.menu = useService("menu");
        this.sidebarRef = useRef("sidebar");
        // Same fallback as the sidebar (search_apps.js) - kept here too since the
        // Home Menu grid can be reached before the navbar's own patch has run
        // (e.g. a direct deep link straight into this action).
        this.menu.getApps().forEach(ensureAppIcon);
    }

    getIconClass(appName) {
        if (!appName) return 'app';
        const iconMap = {
            'Discuss': 'chat-dots',
            'Calendar': 'calendar3',
            'Contacts': 'person-lines-fill',
            'CRM': 'graph-up-arrow',
            'Sales': 'cart-fill',
            'Website': 'globe',
            'Inventory': 'box-seam',
            'Purchase': 'bag-check-fill',
            'Manufacturing': 'tools',
            'Repair': 'wrench-adjustable',
            'Accounting': 'calculator',
            'Project': 'journal-check',
            'Employees': 'people-fill',
            'Expenses': 'cash-stack',
            'Appraisal': 'star-fill',
            'Time Off': 'sun-fill',
            'Attendance': 'clock-history',
            'Recruitment': 'person-badge',
            'Knowledge': 'book-half',
            'Planning': 'map-fill',
            'Helpdesk': 'headset',
            'Field Service': 'briefcase-fill',
            'Quality': 'patch-check',
            'Fleet': 'truck',
            'Lunch': 'egg-fried',
            'Events': 'calendar-event',
            'Surveys': 'pencil-square',
            'Subscriptions': 'arrow-repeat',
            'Documents': 'folder-fill',
            'Sign': 'pencil-fill',
            'Studio': 'layers-fill',
            'Settings': 'gear-fill',
            'Dashboards': 'speedometer2',
            'Point of Sale': 'pc-display-horizontal',
            'Maintenance': 'tools',
            'Marketing Automation': 'megaphone-fill',
            'Email Marketing': 'envelope-paper-heart-fill',
        };
        return iconMap[appName] || 'app';
    }

    onAppClick(app) {
        this.env.bus.trigger('app-selected', { activeApp: app });
        this.menu.selectMenu(app);
    }
}
registry.category("actions").add("nhs_backend_theme.homemenus", HomeMenus);