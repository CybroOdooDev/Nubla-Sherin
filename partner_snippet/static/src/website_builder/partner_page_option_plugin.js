/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rpc } from "@web/core/network/rpc";

export const partnerSnippetSelector = "section.partner-snippet-section";

export class PartnerPageOption extends Plugin {
    static id = "partnerPageOption";

    resources = {
        builder_options: [
            {
                template: "partner_snippet.PartnerPageOption",
                selector: partnerSnippetSelector,
                editableOnly: false,
                title: _t("Partner Page"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: {
            DisplayPartnerMenuAction, // updated reference
        },
    };
}

export class DisplayPartnerMenuAction extends BuilderAction {
    static id = "displayPartnerMenu";
    setup() {
        this.orm = this.services.orm;
        this.currentWebsiteUrl = this.document.location.pathname;
        this.loadPartnerData()
    }

    async prepare() {

        await this.loadPartnerData();
    }

    async loadPartnerData() {
        try {
            const data = await rpc("/get_website_partners", {});
            console.log(data)
            console.log("dataa")
            this.partnerData = data || [];
            this.renderPartnerPreview();
        } catch (error) {
            console.error("Error loading partner data:", error);
        }
    }

    renderPartnerPreview() {
        const container = this.editable.querySelector(partnerSnippetSelector);
        if (!container) return;
        if (!this.partnerData.length) {
            container.innerHTML = `<p class="text-muted">No partner data available.</p>`;
            return;
        }
        container.innerHTML = `
            <div class="partner-list">
                ${this.partnerData.map(
                    (partner) => `
                        <div class="partner-card border rounded p-2 m-1">
                            <h6>${partner.name}</h6>
                            <p>${partner.email || ""}</p>
                        </div>
                    `
                ).join("")}
            </div>
        `;
    }

    async apply() {
        console.log("Applying PartnerPageOption changes...");
        return { reloadUrl: this.document.location.pathname };
    }

    async clean() {
        console.log("Cleaning PartnerPageOption...");
    }
    isApplied() {
        return !!this.partnerData?.length;
    }
}

registry.category("website-plugins").add(PartnerPageOption.id, PartnerPageOption);
