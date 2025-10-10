/** @odoo-module **/

import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

export class PartnerSnippet extends DynamicSnippet {
    static selector = ".s_partner_upcoming_snippet";

    async start() {
        await super.start();

        await this._renderPartnersInEditor();
    }

    async stop() {

        await super.stop();
    }

    dynamicContent = {
        _root: {
            "t-att-data-init": (el) => {
                const name = el.dataset.partnerName || "Unknown Partner";
                return `Loaded: ${name}`;
            },
        },
    };

    async _renderPartnersInEditor() {
        console.log("Rendering partners...");
        const partnerContainer = this.el.querySelector(".s_partner_snippet");
        console.log(this.el)
        console.log(partnerContainer)

        if (!partnerContainer) {
            console.warn(" Partner container not found inside snippet");
            return;
        }

        partnerContainer.innerHTML = `<div class="text-center text-muted">Loading partners...</div>`;

        try {
            const data = await rpc("/get_website_partners", {});
            console.log("datta", data);

            const partners = data.partner_list || [];

            if (partners.length) {
                const fragment = await renderToElement(
                    "partner_snippet.partner_dynamic_template",
                    { partners }
                );
                partnerContainer.innerHTML = "";
                partnerContainer.appendChild(fragment);
            } else {
                partnerContainer.innerHTML = `<div class="col-12 text-center text-muted">No partners available in editor.</div>`;
            }
        } catch (error) {
            console.error(" Error loading partners:", error);
            partnerContainer.innerHTML = `<div class="col-12 text-center text-danger">Failed to load partners in editor.</div>`;
        }
    }
}

registry.category("public.interactions").add(
    "partner_snippet.partner_snippet",
    PartnerSnippet
);

registry.category("public.interactions.edit").add(
    "partner_snippet.partner_snippet",
    { Interaction: PartnerSnippet }
);
