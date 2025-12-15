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
            .replace(/<img([^>]*)>/gi, "<img$1 />")  // Added space before />
            .replace(/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/g, "&amp;")
            .trim();

        const font = this.pos.config.design_receipt_font_style || "Arial";

        // ✅ Safely merge style for .pos-receipt (NO duplicate attributes)
const receiptDivRegex = /<div([^>]*class="pos-receipt"[^>]*)>/i;

if (html.match(/class="pos-receipt"[^>]*style="/i)) {
    // Merge with existing style
    html = html.replace(
        /<div([^>]*class="pos-receipt"[^>]*)style="([^"]*)"/i,
        (match, before, existingStyle) =>
            `<div${before}style="${existingStyle}; font-family:${font}; width:100%">`
    );
} else {
    // Add style if missing
    html = html.replace(
        receiptDivRegex,
        `<div$1 style="font-family:${font}; width:100%">`
    );
}


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
                }
                else if (path.startsWith("partner.")) {
                    value = partner?.[path.slice(8)];
                }
                else if (path.startsWith("company.")) {
                    value = company?.[path.slice(8)];
                }
                else if (path.startsWith("orderline.")) {
    const fieldName = path.slice(10);
    return `<t t-esc="orderline['${fieldName}'] or ''"/>`;
}





                return value !== undefined && value !== null ? String(value) : "";
            }
        );

        return replaced;
    },
get templateProps() {
    const order = this.pos.get_order();
    const receipt = order.export_for_printing();
    console.log("Order",order)
        console.log("receipt",receipt)



    return {
        data: this.props.data,
        order,
        receipt,
        orderlines: receipt.orderlines,
        paymentlines: receipt.paymentlines,
    };
},



    get templateComponent() {
        const design = this.pos.config?.design_receipt || "";
        const xmlString = this.sanitizeReceiptXml(design);
        return class extends Component {
            static template = xml`${xmlString}`;
        };
    },

    get isFalse() {
        return !this.pos.config.is_custom_receipt;
    },
});