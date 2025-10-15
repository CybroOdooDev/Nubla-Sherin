import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

export class ProductSnippet extends DynamicSnippet {
    static selector = ".s_product_upcoming_snippet";

    async start() {
        await super.start();
        await this._renderProductInEditor();
    }

    async stop() {
        const dynamicTemplateEl = this.el.querySelector(".dynamic_snippet_template");
        if (dynamicTemplateEl) {
            dynamicTemplateEl.innerHTML = '';
        }
        await super.stop();
    }
    async willStart() {
    await super.willStart();
    if (!this.snippetOptions?.products) {
        const data = await rpc("/get_website_product", {});
        }
    }
    async _renderProductInEditor() {
        const dynamicTemplateEl = this.el.querySelector(".dynamic_snippet_template");

        if (!dynamicTemplateEl) {
            console.warn("Dynamic snippet template container not found inside snippet");
            return;
        }

        dynamicTemplateEl.innerHTML = `<div class="col-12 text-center text-muted">Loading partners...</div>`;

        try {
            const data = await rpc("/get_website_partners", {});
            const partners = data.partner_list || [];

            if (partners.length) {
                const fragment = await renderToElement(
                    "partner_snippet.partner_dynamic_template",
                    { partners }
                );
                dynamicTemplateEl.innerHTML = "";
                dynamicTemplateEl.appendChild(fragment);
            } else {
                dynamicTemplateEl.innerHTML = `<div class="col-12 text-center text-muted">No partners available.</div>`;
            }
        } catch (error) {
            console.error("Error loading partners:", error);
            dynamicTemplateEl.innerHTML = `<div class="col-12 text-center text-danger">Failed to load partners.</div>`;
        }
    }
}


