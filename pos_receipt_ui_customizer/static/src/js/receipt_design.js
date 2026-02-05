/** @odoo-module **/
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, Component, xml } from "@odoo/owl";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup();
        this.pos = useService("pos");
        this.notification = useService("notification");
        this.state = useState({ template: true });
    },

    sanitizeReceiptXml(xmlString) {
        if (!xmlString) return "";
        try {
            const parser = new DOMParser();
            const parsed = parser.parseFromString(xmlString, "text/html");

            // If the design HTML is reset (e.g. after upgrade), but the config still says
            // we have extra columns, we re-inject them on the fly.
            const selectedFieldsStr = this.pos.config?.selected_product_fields || "[]";
            let selectedFields = [];
            try {
                selectedFields = JSON.parse(selectedFieldsStr);
            } catch (e) {
                selectedFields = [];
            }

            if (selectedFields.length > 0) {
                const table = parsed.querySelector(".receipt-table");
                const headerRow = table?.querySelector("thead tr");
                if (headerRow) {
                    selectedFields.forEach(field => {
                        // Only add if not already there
                        if (!headerRow.querySelector(`th[data-field="${field}"]`)) {
                            const th = document.createElement("th");
                            th.setAttribute("data-field", field);
                            th.style.textAlign = "center";
                            th.style.fontSize = "12px";
                            th.style.padding = "4px";
                            // Auto-generate label: product_code -> Product Code
                            th.textContent = field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                            headerRow.appendChild(th);
                        }
                    });
                }
            }
            // ---------------------------

            let html = parsed.body.innerHTML
                .replace(/<br\s*>/gi, "<br/>")
                .replace(/<hr\s*>/gi, "<hr/>")
                .replace(/&nbsp;|\u00A0/g, " ")
                .replace(/<img([^>]*)>/gi, "<img$1/>")
                .replace(/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/g, "&amp;")
                .trim();

            const font = this.pos.config?.design_receipt_font_style || "Arial";
            html = html.replace(/<div([^>]*class="pos-receipt"[^>]*)>/i,
                (m, attrs) =>
                    `<div ${attrs.replace(/\s*style="[^"]*"/gi, "")} style="font-family:${font};">`
            );

            const order = this.pos.get_order();
            const receipt = order?.export_for_printing?.() || {};
            const partner = order?.get_partner?.();
            const company = this.pos.company;

            html = html
                .replaceAll('[[ receipt.total_without_tax ]]',
                    this.env.utils.formatCurrency(receipt.total_without_tax || 0))
                .replaceAll('[[ receipt.amount_total ]]',
                    this.env.utils.formatCurrency(receipt.amount_total || 0));

            const replaced = html.replace(
                /\[\[\s*([\w.\s]+)\s*\]\]/g,
                (match, fieldPath) => {
                    const path = fieldPath.trim().replace(/\s+/g, "");
                    let value = "";

                    if (path.startsWith("order.")) {
                        value = order?.[path.slice(6)];
                    } else if (path.startsWith("partner.")) {
                        value = partner?.[path.slice(8)];
                    } else if (path.startsWith("company.")) {
                        value = company?.[path.slice(8)];
                    }

                    return value ? value : match;
                }
            );

            return replaced;
        } catch (error) {
            console.error("Error sanitizing receipt XML:", error);
            return "";
        }
    },
    get templateProps() {
        const order = this.pos.get_order();

        if (!order) {
            return {
                data: this.props.data,
                order: null,
                receipt: {},
                orderlines: [],
                paymentlines: [],
                dynamic_fields: [],
            };
        }

        const receipt = order.export_for_printing();

        const dynamicFields = [
            ...new Set(
                (receipt.dynamic_fields || [])
                    .map(f => {
                        if (typeof f === 'string') return f.trim();
                        if (typeof f === 'object' && f.name) return f.name.trim();
                        return null;
                    })
                    .filter(Boolean)
            )
        ];

        const jsOrderlines = order.get_orderlines() || [];

        const orderlines = (receipt.orderlines || []).map(line => {
            let currentOrderline = jsOrderlines.find(ol => ol.cid === line.cid);

            if (!currentOrderline && line.product_id) {
                currentOrderline = jsOrderlines.find(ol =>
                    ol.product?.id === line.product_id
                );
            }

            const product = currentOrderline?.product ||
                currentOrderline?.get_product?.() ||
                this.pos.db.get_product_by_id(line.product_id);

            const dynamicValues = {};
            dynamicFields.forEach(field => {
                dynamicValues[field] =
                    line[field] ||
                    currentOrderline?.[field] ||
                    product?.[field] ||
                    '';
            });

            return {
                ...line,
                product,
                _dynamicValues: dynamicValues,

            };
        });

        return {
            data: this.props.data,
            order,
            receipt,
            orderlines,
            paymentlines: receipt.paymentlines || [],
            dynamic_fields: dynamicFields,
        };
    },
    get templateComponent() {
        try {
            const design = this.pos.config?.design_receipt || "";
            if (!design) return null;

            const xmlString = this.sanitizeReceiptXml(design);
            if (!xmlString) return null;

            return class extends Component {
                static template = xml`${xmlString}`;
                static props = {
                    data: { type: Object, optional: true },
                    order: { type: Object, optional: true },
                    receipt: { type: Object, optional: true },
                    orderlines: { type: Array, optional: true },
                    paymentlines: { type: Array, optional: true },
                    dynamic_fields: { type: Array, optional: true },
                };
            };
        } catch (error) {
            console.error("Error creating receipt component:", error);
            return null;
        }
    },

    get isFalse() {
        const config = this.pos.config;
        if (!config) return true;

        const isCustom = config.is_custom_receipt;
        const design = config.design_receipt;

        // Return true (show standard) IF custom is disabled OR design is missing
        return !isCustom || !design || !design.trim();
    },
});