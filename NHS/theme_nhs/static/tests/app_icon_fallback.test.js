/** @odoo-module **/

import { describe, expect, test } from "@odoo/hoot";
import { ensureAppIcon } from "@theme_nhs/js/app_icon_fallback";
import { HomeMenus } from "@theme_nhs/js/home_menus";

describe("theme_nhs > app_icon_fallback", () => {
    test("does not crash when app object is null or undefined", () => {
        expect(() => ensureAppIcon(null)).not.toThrow();
        expect(() => ensureAppIcon(undefined)).not.toThrow();
    });

    test("keeps existing valid custom icon unchanged", () => {
        const app = {
            name: "CustomApp",
            webIconData: "data:image/png;base64,iVBORw0KGgo...",
        };
        ensureAppIcon(app);
        expect(app.webIconData).toBe("data:image/png;base64,iVBORw0KGgo...");
    });

    test("derives fallback icon path from xmlid when webIconData is missing", () => {
        const app = {
            name: "TestModule",
            xmlid: "theme_nhs.menu_root",
            webIconData: false,
        };
        ensureAppIcon(app);
        expect(app.webIcon).toBe("theme_nhs,static/description/icon.png");
        expect(app.webIconData).toBe("/theme_nhs/static/description/icon.png");
    });

    test("replaces default cardboard box icon with module icon", () => {
        const app = {
            name: "BoxApp",
            xmlid: "my_module.main_menu",
            webIconData: "/web/static/img/default_icon_app.png",
        };
        ensureAppIcon(app);
        expect(app.webIcon).toBe("my_module,static/description/icon.png");
        expect(app.webIconData).toBe("/my_module/static/description/icon.png");
    });

    test("derives fallback from webIcon string with comma", () => {
        const app = {
            name: "OtherApp",
            webIcon: "other_module,static/description/icon.png",
            webIconData: null,
        };
        ensureAppIcon(app);
        expect(app.webIcon).toBe("other_module,static/description/icon.png");
        expect(app.webIconData).toBe("/other_module/static/description/icon.png");
    });
});

describe("theme_nhs > HomeMenus helper methods", () => {
    test("getIconClass returns mapped icon or fallback", () => {
        const instance = new HomeMenus();
        expect(instance.getIconClass("Discuss")).toBe("chat-dots");
        expect(instance.getIconClass("Calendar")).toBe("calendar3");
        expect(instance.getIconClass("Contacts")).toBe("person-lines-fill");
        expect(instance.getIconClass("CRM")).toBe("graph-up-arrow");
        expect(instance.getIconClass("UnknownApp")).toBe("app");
        expect(instance.getIconClass(null)).toBe("app");
    });
});

