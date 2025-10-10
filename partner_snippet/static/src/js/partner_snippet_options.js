/** @odoo-module **/

import { DynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_option";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

DynamicSnippetOption.registry.PartnerSnippetOptions = DynamicSnippetOption.Class.extend({
   async start() {
       await this._super(...arguments);
       this._renderPartnersInEditor();
   },

   async _renderPartnersInEditor() {
       const partnerContainer = this.$target.find("#partner-dynamic-content-container");

       if (!partnerContainer.length) return;
       partnerContainer.html(`<div class="text-center text-muted">Loading partners in editor...</div>`);

       try {
           const data = await rpc("/get_website_partners", {});
           console.log("datta",data)
           const partners = data.partner_list;

           if (partners && partners.length > 0) {
               const fragment = await renderToElement("partner_snippet.partner_dynamic_template", { partners });
               partnerContainer.empty().append(fragment);
           } else {
               partnerContainer.html(`<div class="col-12 text-center text-muted">No partners available in editor.</div>`);
           }
       } catch (error) {
           partnerContainer.html(`<div class="col-12 text-center text-danger">Failed to load partners in editor.</div>`);
       }
   },
});

