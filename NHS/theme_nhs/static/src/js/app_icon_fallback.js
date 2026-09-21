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
    if (app.webIcon || !app.xmlid) {
        return;
    }
    const moduleName = app.xmlid.split(".")[0];
    app.webIcon = `${moduleName},static/description/icon.png`;
    app.webIconData = `/${moduleName}/static/description/icon.png`;
}
