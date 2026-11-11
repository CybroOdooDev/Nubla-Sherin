/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("theme_nhs_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Check that the main navbar is rendered",
            trigger: ".o_main_navbar",
        },
        {
            content: "Click Home Menu button to toggle the NHS app drawer",
            trigger: "button[title='Home Menu'], button[data-hotkey='h']",
            run: "click",
        },
        {
            content: "Verify that the Home Menu container is visible",
            trigger: ".app_container .app_list",
        },
        {
            content: "Click on an application icon in the NHS Home Menu",
            trigger: ".app_list .app_wrapp:first-child",
            run: "click",
        },
        {
            content: "Verify that the sidebar is visible after app selection",
            trigger: ".sidebar:not(.o_hidden)",
        },
    ],
});

