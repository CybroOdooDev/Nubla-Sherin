/** @odoo-module **/

import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOptions } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { DynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_option";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

export class DynamicSnippetPartnerOption extends BaseOptionComponent {
    static template = "partner_snippet.DynamicSnippetPartnerOption";
    static props = {
        ...DynamicSnippetOption.props,
    };

    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOptions(this.props.modelNameFilter);
        this._renderPartnersInEditor();
    }

    /**
     * Load partners immediately inside editor (before save)
     */
    async _renderPartnersInEditor() {
        const container = this.el.querySelector("#partner-dynamic-content-container");
        if (!container) return;

        container.innerHTML = `<div class="text-center text-muted">Loading partners in editor...</div>`;

        try {
            const data = await rpc("/get_website_partners", {});
            console.log("Datat...",data)
            const partners = data.partner_list || [];

            if (partners.length > 0) {
                const fragment = await renderToElement(
                    "partner_snippet.partner_dynamic_template",
                    { partners }
                );
                container.innerHTML = "";
                container.appendChild(fragment);
            } else {
                container.innerHTML = `<div class="col-12 text-center text-muted">No partners available in editor.</div>`;
            }
        } catch (error) {
            container.innerHTML = `<div class="col-12 text-center text-danger">Failed to load partners in editor.</div>`;
            console.error("Partner snippet load error:", error);
        }
    }
}
