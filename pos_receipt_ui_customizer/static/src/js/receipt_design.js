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
    const parser = new DOMParser();
    const parsed = parser.parseFromString(xmlString, "text/html");
    let html = parsed.body.innerHTML
        .replace(/<br\s*>/gi, "<br/>")
        .replace(/<hr\s*>/gi, "<hr/>")
        .replace(/&nbsp;|\u00A0/g, " ")
        .replace(/<img([^>]*)>/gi, "<img$1/>")
        .replace(/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/g, "&amp;")
        .trim();

    const font = this.pos.config.design_receipt_font_style || "Arial";
    html = html.replace(/<div([^>]*class="pos-receipt"[^>]*)>/i,
        (m, attrs) =>
            `<div ${attrs.replace(/\s*style="[^"]*"/gi, "")} style="font-family:${font};">`
    );

    const order = this.pos.get_order();
    const receipt = order.export_for_printing();
    const partner = order.get_partner();
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

            // ✅ KEEP dynamic placeholders
            return value ? value : match;
        }
    );

    return replaced;
},
    get templateProps() {
    const order = this.pos.get_order();
    const receipt = order.export_for_printing();

    const dynamicFields = (receipt.dynamic_fields || [])
        .map(f => {
            if (typeof f === 'string') return f.trim();
            if (typeof f === 'object') return f.name;
            return '';
        })
        .filter(Boolean);

    const orderlines = (receipt.orderlines || []).map(line => {
        const dynamicValues = {};
        dynamicFields.forEach(field => {
            dynamicValues[field] = line[field] ?? '';
        });
        return {
            ...line,
            _dynamicValues: dynamicValues,
        };
    });

    console.log("Dynamic fields:", dynamicFields);
    console.log("Orderlines (enriched):", orderlines[0].barcode);

    return {
        data: this.props.data,
        order,
        receipt,
        orderlines,
        paymentlines: receipt.paymentlines,
        dynamic_fields: dynamicFields,
    };
},

    get templateComponent() {
        const design = this.pos.config?.design_receipt || "";
        const xmlString = this.sanitizeReceiptXml(design);

        // ✅ Fixed typo: xm -> xml
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
    },

    get isFalse() {
        return !this.pos.config.is_custom_receipt;
    },
});