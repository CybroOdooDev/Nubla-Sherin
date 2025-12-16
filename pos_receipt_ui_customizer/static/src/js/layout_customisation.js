/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted,onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PosReceiptLayoutClientAction extends Component {
    static template = "custom_receipt_for_pos.client_layout_customisation_template";
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.receiptContentRef = useRef("ReceiptContent");
        this.inputRef = useRef("userInput");
        this.selectedProductFields = [];

        this.receipt_id = this.props.action?.params?.receipt_id || this.props.action?.context?.active_id;
//        this.receipt_id = this.props.action.context.active_id;
        this.state = useState({
            fontStyle: "Arial",
            fields: [],
            logo: '',
            prev_logo: '',
            prev_receipt: '',
            receipt: '',
            model: '',
            showSection: false,
            showSection1: true,
// ✅ NEW: popup state
    popup: {
        visible: false,
        x: 0,
        y: 0,
        type: null,          // "column" or "cell"
        columnIndex: null,   // clicked column index
        selectedField: "",   // e.g. "order.amount_total"
    },
        });
           onWillStart(async () => {
    await this.loadProductFields();
});

        onMounted(async () => {
            await this.loadReceipt();
            this.mediumEditor();
            this.preventPartialSelection();
            this.allowSpace();
        });


    }

    async mediumEditor() {
        this.editor = new MediumEditor(this.receiptContentRef.el, {
            toolbar: {
                buttons: ['bold', 'italic', 'underline', 'strikethrough', 'subscript', 'superscript', 'h1', 'h3', 'quote', 'anchor'],
            },
            placeholder: false,
            targetBlank: true,
            disableExtraSpaces: true,
        });
    }

    async allowSpace(){
        this.receiptContentRef.el.addEventListener("keydown", (ev) => {
            if (ev.key === " " || ev.keyCode === 32) {
                const sel = window.getSelection();
                if (!sel.rangeCount) return;
                const range = sel.getRangeAt(0);
                if (
                    range.startContainer.nodeType === Node.TEXT_NODE &&
                    range.startOffset === range.startContainer.length
                ) {
                    ev.preventDefault();
                    document.execCommand("insertHTML", false, "&nbsp;");
                }
            }
        });
    }

    preventPartialSelection() {
        document.addEventListener("selectionchange", () => {
            const sel = window.getSelection();
            if (!sel.rangeCount) return;
            const range = sel.getRangeAt(0);
            const startEl = range.startContainer.parentElement;
            const endEl = range.endContainer.parentElement;
            const placeholder = startEl.closest(".placeholder-span") || endEl.closest(".placeholder-span");
            if (placeholder && sel.toString() !== placeholder.textContent) {
                const newRange = document.createRange();
                newRange.selectNodeContents(placeholder);
                sel.removeAllRanges();
                sel.addRange(newRange);
            }
        });
    }

    async loadReceipt(reset=false) {
        const [receipt] = await this.orm.searchRead(
            "pos.receipt",
            [["id", "=", this.receipt_id]],
            ["name", "design_receipt", "design_receipt_font_style", "logo"]
        );
        if (!receipt) return;
        this.state.fontStyle = receipt.design_receipt_font_style || "Arial";
        this.state.logo = receipt.logo
        if (!reset && this.receiptContentRef.el?.innerHTML) {
            this.state.receipt = this.receiptContentRef.el.innerHTML;
        }
        else {
            this.state.receipt = receipt.design_receipt;
        }
        let html = this.state.receipt
        let logo;
        if (reset === false || !this.state.prev_logo) {
            logo = this.state.logo;
        } else {
            logo = this.state.prev_logo;
        }
        this.state.logo = logo;
        html = html.replace(/<img[^>]*class="receipt-logo"[^>]*>/gi, "");
        html = html.replace(/<t t-else="">\s*<\/t>/gi, "");
        html = html.replace(/<t>\s*<\/t>/gi, "");
        if (logo) {
            html = html.replace(
                /<t t-if="env.services.pos.config.logo">[\s\S]*?<\/t>/,
                `<t t-if="env.services.pos.config.logo">
                    <img t-att-src="'data:image/png;base64,' + env.services.pos.config.logo"
                         class="pos-receipt-logo"/>
                </t>
                <t t-else="">
                <img src="data:image/png;base64,${logo}"
                     class="receipt-logo" style="max-width:150px;height:auto;"/>
                </t>`

            );
        }
        this.receiptContentRef.el.innerHTML = html;
    }

    triggerImageUpload() {
        document.getElementById("imageUpload")?.click();
    }

    async insertImage(ev) {
        const file = ev.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async () => {
            const base64 = reader.result.split(",")[1];
            this.state.receipt = this.receiptContentRef.el.innerHTML;
            this.state.prev_logo = this.state.logo;
            this.state.prev_receipt = this.state.receipt;
            await this.orm.write("pos.receipt", [this.receipt_id], { logo: base64 });
            this.state.logo = base64;
            await this.loadReceipt();
            this.notification.add("✅ Receipt Logo Updated!", {
                type: "success",
            });
        };
        reader.readAsDataURL(file);
    }

    async saveEditedReceipt() {
        this.state.receipt = this.receiptContentRef.el.innerHTML
        this.state.prev_logo = this.state.logo
        this.state.prev_receipt = this.state.receipt
        const html = this.state.receipt
        await this.orm.write("pos.receipt", [this.receipt_id], {
            design_receipt: html,
            design_receipt_font_style: this.state.fontStyle,
            logo: this.state.logo,
        });
        this.notification.add("✅ Receipt Successfully Updated!", {
                type: "success",
            });
    }

    async resetEditedReceipt(){
        if (this.state.prev_receipt) {
            this.state.receipt = this.state.prev_receipt;
            this.receiptContentRef.el.innerHTML = this.state.receipt;
        }
       await this.loadReceipt(true);
       this.notification.add("🔄 Receipt Reset Completed!", {
           type: "success",
       });
    }

    onFontChange(ev) {
        this.state.fontStyle = ev.target.value;
    }

    async onModelChange(ev) {
        const model = ev.target.value;
        this.state.model = model
        if (!model) return (this.state.fields = []);
            const fields = await this.orm.call(model, "fields_get", [], {});
            this.state.fieldsInfo = fields;
            const prefix = model === "pos.order" ? "order" :
                           model === "res.partner" ? "partner" : model;
            this.state.fields = Object.keys(fields).filter(key => !/(_ids?$|\d+$)/.test(key)).map((key) => ({
                technical: `${prefix}.${key}`,
                label: odoo.debug
                    ? `${fields[key].string || key} (${prefix}.${key})`
                    : fields[key].string || key,
            }));
    }

    onDragStart(ev) {
        const field = `[[${ev.target.dataset.field}]]`;
        ev.dataTransfer.setData("text/plain", field);
        ev.dataTransfer.effectAllowed = "copy";
        const ghost = document.createElement("div");
        ghost.textContent = field;
        ghost.style.padding = "6px 12px";
        ghost.style.fontSize = "12px";
        ghost.style.fontWeight = "400";
        ghost.style.background = "#e8f1ff";
        ghost.style.color = "black";
        ghost.style.borderRadius = "20px";
        ghost.style.boxShadow = "0 2px 6px rgba(0,0,0,0.15)";
        ghost.style.pointerEvents = "none";
        ghost.style.position = "absolute";
        ghost.style.top = "-9999px";
        ghost.style.left = "-9999px";
        document.body.appendChild(ghost);
        ev.dataTransfer.setDragImage(ghost, 0, 0);
        setTimeout(() => ghost.remove(), 0);
        this.receiptContentRef.el.classList.add("dragging");
        this.receiptContentRef.el.classList.add("drop-highlight");
    }

    onDragEnd() {
            this.receiptContentRef.el.classList.remove("dragging");
            this.receiptContentRef.el.classList.remove("drop-highlight");
        }

    onDrop(ev) {
        ev.preventDefault();
        const editor = this.receiptContentRef.el;
        const fieldText = ev.dataTransfer.getData("text/plain");
        if (!fieldText) return;
        const span = document.createElement("span");
        span.textContent = fieldText;
        span.classList.add("placeholder-span");
        const placeholder = ev.target.closest(".placeholder-span");
        if (placeholder) {
            placeholder.insertAdjacentElement("afterend", span);
            return;
        }
        let range = null;
        if (document.caretRangeFromPoint) {
            range = document.caretRangeFromPoint(ev.clientX, ev.clientY);
        } else if (document.caretPositionFromPoint) {
            const pos = document.caretPositionFromPoint(ev.clientX, ev.clientY);
            if (pos?.offsetNode) {
                range = document.createRange();
                range.setStart(pos.offsetNode, pos.offset);
                range.collapse(true);
            }
        }
        if (range) {
            range.insertNode(span);
        }
        else {
            let targetArea = editor.querySelector(".drop-area")
            if (targetArea) {
                targetArea.appendChild(span);
            }
        }
        this.receiptContentRef.el.classList.remove("dragging");
        this.receiptContentRef.el.classList.remove("drop-highlight");
        span.classList.add("added");
        setTimeout(() => span.classList.remove("added"), 400);
    }


//    insertDemoQR() {
//	    const editor = this.receiptContentRef.el;
//
//	    // Prevent multiple QR codes
//	    if (editor.querySelector(".qr-placeholder")) {
//		this.notification.add("A QR code already exists!", { type: "warning" });
//		return;
//	    }
//	    let targetArea = editor.querySelector(".qrArea")
//
//	    // Create wrapper
//	    const qrDiv = document.createElement("div");
//	    qrDiv.classList.add("qr-placeholder");
//	    qrDiv.style.textAlign = "center";
//	    qrDiv.style.marginTop = "10px";
//
//	    // Create inner div for QR generation
//	    const qrBox = document.createElement("div");
//	    qrBox.id = "qr_" + Date.now();  // unique ID
//	    qrDiv.appendChild(qrBox);
//
//	    // Add to editor
//	    targetArea.appendChild(qrDiv);
//
//	    new QRCode(qrBox, {
//		text: "Demo QR",
//		width: 120,
//		height: 120,
//	    });
//
//	}
        showInput() {
            this.state.showSection = true;
            this.state.showSection1 = false;
        }

        submitValue() {
            const value = this.inputRef.el.value;

            if (!value) {
                this.notification.add("Please enter a value!", { type: "warning" });
                return;
            }

            const editor = this.receiptContentRef.el;

            const oldQR = editor.querySelector(".qr-placeholder");
            if (oldQR) {
                oldQR.remove();
            }

            let targetArea = editor.querySelector(".qrArea");
            if (!targetArea) {
                this.notification.add("No target area found!", { type: "danger" });
                return;
            }

            const qrDiv = document.createElement("div");
            qrDiv.classList.add("qr-placeholder");
            qrDiv.style.textAlign = "center";
            qrDiv.style.marginTop = "10px";

            // 6. Inner div for QR
            const qrBox = document.createElement("div");
            qrBox.id = "qr_" + Date.now();   // unique ID
            qrDiv.appendChild(qrBox);

            // 7. Add to editor
            targetArea.appendChild(qrDiv);

            // 8. Generate QR code
            new QRCode(qrBox, {
                text: value,
                width: 120,
                height: 120,
            });

            // OPTIONAL: Hide input section after submitting
            this.state.showSection = false;
            this.state.showSection1 = true;
        }



    onReceiptClick(ev) {
        // Only care about clicks inside tables in the editor
        const td = ev.target.closest("td");
        const th = ev.target.closest("th");
        const table = ev.target.closest("table");

        // Clicked somewhere in the editor but not on a table
        if (!table) {
            this.hidePopup();
            this.lastClickedCell = null;
            this.lastClickedTable = null;
            return;
        }

        // Remember the clicked table so we edit the right one
        this.lastClickedTable = table;

        // Header cell → column mode
        if (th) {
            const index = Array.from(th.parentNode.children).indexOf(th);
            this.lastClickedCell = null;
            this.showPopup("column", ev.clientX, ev.clientY, index);
            return;
        }

        // Body cell → cell mode
        if (td) {
            const index = Array.from(td.parentNode.children).indexOf(td);
            this.lastClickedCell = td;
            this.showPopup("cell", ev.clientX, ev.clientY, index);
            return;
        }

        // Clicked table but not on td/th
        this.hidePopup();
    }

    showPopup(type, x, y, columnIndex) {
        this.state.popup.visible = true;
        this.state.popup.x = x;
        this.state.popup.y = y;
        this.state.popup.type = type;
        this.state.popup.columnIndex = columnIndex;
    }

    hidePopup() {
        this.state.popup.visible = false;
        this.state.popup.type = null;
        this.state.popup.columnIndex = null;
    }







    async loadProductFields() {
    const fields = await this.orm.call("product.product", "fields_get", [], {});

    this.state.productFields = Object.keys(fields)
        .filter(k => !/(_ids?$|\d+$)/.test(k))
        .map(k => ({
            name: k,
            label: fields[k].string || k,
        }));
}




    onPopupFieldChange(ev) {
        this.state.popup.selectedField = ev.target.value || "";
    }

  async onAddColumnClick() {
    const fieldName = this.state.popup.selectedField;
    console.log("Selected field:", fieldName);

    if (!fieldName) {
        this.notification.add("Please select a field.", { type: "warning" });
        return;
    }
    if (!this.lastClickedTable) {
        this.notification.add("Click a table first.", { type: "danger" });
        return;
    }
    if (!this.receipt_id) {
        this.notification.add("Receipt ID not found", { type: "danger" });
        return;
    }

    const table = this.lastClickedTable;
    let headerRow = table.querySelector("thead tr") || table.querySelector("tr");
    if (!headerRow) return;

    let bodyRows = table.querySelectorAll("tbody tr");
    if (!bodyRows.length) {
        bodyRows = Array.from(table.querySelectorAll("tr")).slice(1);
    }

    const insertIndex =
        typeof this.state.popup.columnIndex === "number"
            ? this.state.popup.columnIndex + 1
            : headerRow.children.length;

            const fieldObj = this.state.productFields.find(f => f.name === fieldName);
            const label = fieldObj?.label || fieldName;

            if (!this.selectedProductFields.includes(fieldName)) {
                this.selectedProductFields.push(fieldName);
            }

            const th = document.createElement("th");
            th.textContent = label;
            th.setAttribute("data-field", fieldName);
            headerRow.insertBefore(th, headerRow.children[insertIndex] || null);

            bodyRows.forEach((row) => {
                const td = document.createElement("td");
                td.setAttribute("data-field", fieldName);
                td.style.padding = "4px";

                const span = document.createElement("span");
//                span.textContent = `[[ orderline.${fieldName} ]]`;
//                span.setAttribute("t-esc", `orderline.${fieldName}`);

                td.appendChild(span);

                row.insertBefore(td, row.children[insertIndex] || null);
            });

            await this.orm.write("pos.receipt", [this.receipt_id], {
                selected_product_fields: JSON.stringify(this.selectedProductFields),
            });

            console.log(" Saved fields:", this.selectedProductFields);

            const result = await this.orm.read(
            "pos.receipt",
            [this.receipt_id],
            ["selected_product_fields"]
         );

        console.log("DB value:", result[0].selected_product_fields);
            this.hidePopup();
        }

    saveDesignToConfig() {
        const receiptDiv = document.querySelector('.pos-receipt');
        if (!receiptDiv) {
            console.error("Receipt div not found");
            return;
        }

        let updatedDesign = receiptDiv.outerHTML;
        updatedDesign = updatedDesign
            .replace(/\sdata-[^=]*="[^"]*"/g, '')
            .replace(/\sclass="[^"]*"/g, (match) => {
                if (match.includes('pos-receipt') || match.includes('placeholder-span')) {
                    return match;
                }
                return '';
            });

        // ✅ Extract selected fields from the design
        const selectedFields = this.extractFieldsFromDesign(updatedDesign);

        this.orm
            .call('pos.receipt', 'write', [[this.receipt_id], {
                design_receipt: updatedDesign,
                selected_product_fields: JSON.stringify(selectedFields),  // ✅ Save fields
            }])
            .then(() => {
                this.notification.add("Design saved successfully!", { type: "success" });
            })
            .catch((error) => {
                console.error("Save error:", error);
                this.notification.add("Failed to save", { type: "danger" });
            });
    }

    // ✅ Extract fields from design HTML
    extractFieldsFromDesign(html) {
        const fields = new Set();
        const regex = /\[\[\s*orderline\.([\w_]+)\s*\]\]/g;
        let match;

        while ((match = regex.exec(html)) !== null) {
            fields.add(match[1]);
        }

        return Array.from(fields);
    }
    onRemoveColumnClick() {
        if (!this.lastClickedTable) {
            this.notification.add("No table selected.", { type: "danger" });
            this.hidePopup();
            return;
        }

        const table = this.lastClickedTable;
        const theadRow = table.querySelector("thead tr");
        const bodyRows = table.querySelectorAll("tbody tr");
        if (!theadRow) {
            this.notification.add("Table does not have a header row.", {
                type: "danger",
            });
            this.hidePopup();
            return;
        }

        const colIndex = this.state.popup.columnIndex;
        if (colIndex == null || colIndex < 0) {
            this.notification.add("Invalid column selection.", { type: "danger" });
            this.hidePopup();
            return;
        }

        // Remove header cell
        if (theadRow.children[colIndex]) {
            theadRow.removeChild(theadRow.children[colIndex]);
        }

        // Remove body cells
        bodyRows.forEach((row) => {
            if (row.children[colIndex]) {
                row.removeChild(row.children[colIndex]);
            }
        });

        this.hidePopup();
    }


    onInsertFieldClick() {
        const fieldTechnical = this.state.popup.selectedField;
        if (!fieldTechnical) {
            this.notification.add("Please select a field to insert.", {
                type: "warning",
            });
            return;
        }
        if (!this.lastClickedCell) {
            this.notification.add("No cell selected to insert into.", {
                type: "danger",
            });
            this.hidePopup();
            return;
        }

        const cell = this.lastClickedCell;

        // If cell only has spaces/newlines, clear it
        if (!cell.textContent.trim()) {
            cell.innerHTML = "";
        }

        const span = document.createElement("span");
        span.classList.add("placeholder-span");
        span.textContent = `[[${fieldTechnical}]]`;

        if (cell.lastChild) {
            cell.appendChild(document.createTextNode(" "));
        }
        cell.appendChild(span);

        if (this._animateSpan) {
            this._animateSpan(span);
        }

        this.hidePopup();
    }

}
registry.category("actions").add("pos_receipt_layout_client_action", PosReceiptLayoutClientAction);