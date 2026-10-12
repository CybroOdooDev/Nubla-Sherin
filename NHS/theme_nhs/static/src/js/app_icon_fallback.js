/** @odoo-module */

// Odoo only serves a real app icon (sidebar rail, app grid) when a module's
// root menu explicitly sets `web_icon="module,static/description/icon.png"`
// on its <menuitem>. Every module in this suite already ships that icon.png
// (it's what the Apps list uses), but a handful never got the matching
// `web_icon` attribute wired up - and without it, `app.webIcon`/`webIconData`
// come back empty, so both nav.scss templates fall through to their generic
// glyph fallback (Bootstrap's "bi-app", a blank rounded square) instead of
// showing anything real. Rather than requiring every module to remember to
// set web_icon, derive the same path Odoo would have used from the app's own
// xmlid ("module_name.menu_xxx_id") whenever it's missing.
export function ensureAppIcon(app) {
    if (!app) {
        return;
    }
    // If the app already has real custom image data (e.g. base64 data URI), keep it.
    // If it's empty, null, or pointing to Odoo's default cardboard box icon ("/web/static/img/default_icon_app.png"),
    // we override it with the module's real app icon.
    const isDefaultBox = !app.webIconData || (typeof app.webIconData === "string" && app.webIconData.includes("default_icon_app"));
    const hasValidCustomIcon = app.webIconData && typeof app.webIconData === "string" && !isDefaultBox;

    if (hasValidCustomIcon) {
        return;
    }

    // Determine module name from xmlid or webIcon
    const xmlId = app.xmlid || app.xmlID;
    let moduleName = "";
    if (xmlId && xmlId.includes(".")) {
        moduleName = xmlId.split(".")[0];
    } else if (typeof app.webIcon === "string" && app.webIcon.includes(",")) {
        moduleName = app.webIcon.split(",")[0].trim();
    }

    if (moduleName) {
        app.webIcon = `${moduleName},static/description/icon.png`;
        app.webIconData = `/${moduleName}/static/description/icon.png`;
    }
}

