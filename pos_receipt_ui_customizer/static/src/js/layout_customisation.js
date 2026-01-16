/** @odoo-module **/
import {registry} from "@web/core/registry";
import {Component, useState, useRef, onMounted, onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


class PosReceiptLayoutClientAction extends Component {
    static template = "custom_receipt_for_pos.client_layout_customisation_template";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.receiptContentRef = useRef("ReceiptContent");
        this.inputRef = useRef("userInput");
        this.selectedProductFields = [];
        this.config_id =
            this.props.action?.params?.config_id ||
            this.props.action?.context?.pos_config_id ||
            this.props.action?.context?.active_id;
        this.dialog = useService("dialog");
        this.lastClickedTable = null;
    this.lastClickedColumnIndex = null;


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
            headerFields: [],
            draggedField: null,

            popup: {
                visible: false,
                x: 0,
                y: 0,
                type: null,
                columnIndex: null,
                selectedField: "",
            },

        });



        onWillStart(async () => {

            await this.loadProductFields();
            await this.loadPosConfigId();
            await this.loadEnableQr();
        });

        onMounted(async () => {
            await this.loadReceipt();
            this.mediumEditor();
            this.preventPartialSelection();
            this.allowSpace();
             this.enableColumnDropZones();
             this.restoreSavedColumns();
             if (this.state.enableQr) {
            this.renderReceiptQr();
                }
        });

    }




        renderReceiptQr() {
    if (!this.state.enableQr) return;

    const editor = this.receiptContentRef.el;
    if (!editor) return;

    const wrapper = editor.querySelector(".receipt-qr-wrapper");
    if (!wrapper) return;

    wrapper.querySelector(".receipt-qr-placeholder")?.remove();

    const templateImg = wrapper.querySelector(".receipt-qr-template img");
    if (!templateImg) return;

    const qrDiv = document.createElement("div");
    qrDiv.className = "receipt-qr-placeholder";
    qrDiv.style.textAlign = "center";
    qrDiv.style.marginTop = "12px";

    const img = templateImg.cloneNode(true);
    img.style.width = "120px";
    img.style.height = "120px";

    if (!this.props.data?.custom_qr_image) {
        const tempContainer = document.createElement('div');
        tempContainer.style.position = 'absolute';
        tempContainer.style.left = '-9999px';  // Hide off-screen
        tempContainer.style.width = '120px';
        tempContainer.style.height = '120px';
        document.body.appendChild(tempContainer);

        new QRCode(tempContainer, {
            text: "Demo Receipt QR",
            width: 120,
            height: 120,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.H
        });

        const qrCanvas = tempContainer.querySelector('canvas');
        const demoSrc = qrCanvas ? qrCanvas.toDataURL('image/png') : '';
        img.setAttribute('src', demoSrc);

        document.body.removeChild(tempContainer);
    }

    qrDiv.appendChild(img);
    wrapper.appendChild(qrDiv);
}


//     renderReceiptQr() {
//     if (!this.state.enableQr) return;
//
//     const editor = this.receiptContentRef.el;
//     if (!editor) return;
//
//     const wrapper = editor.querySelector(".receipt-qr-wrapper");
//     if (!wrapper) return;
//
//     // remove existing
//     wrapper.querySelector(".receipt-qr-placeholder")?.remove();
//
//     const templateImg = wrapper.querySelector(
//         ".receipt-qr-template img"
//     );
//     if (!templateImg) return;
//
//     const qrDiv = document.createElement("div");
//     qrDiv.className = "receipt-qr-placeholder";
//     qrDiv.style.textAlign = "center";
//     qrDiv.style.marginTop = "12px";
//
//     const img = templateImg.cloneNode(true);
//     img.style.width = "120px";
//     img.style.height = "120px";
//
//     qrDiv.appendChild(img);
//     wrapper.appendChild(qrDiv);
// }



    async restoreSavedColumns() {
    if (!this.receipt_id) return;

    const rec = await this.orm.read("pos.receipt", [this.receipt_id], ["selected_product_fields"]);
    const fields = JSON.parse(rec[0]?.selected_product_fields || "[]");

    if (!fields.length) return;

    const table = this.receiptContentRef.el.querySelector(".receipt-table");
    const headerRow = table.querySelector("thead tr");

    headerRow.querySelectorAll("th[data-field]").forEach(th => th.remove());
    table.querySelectorAll("td[data-field]").forEach(td => td.remove());

    fields.forEach(field => {
        this.addColumnAtIndex(field, 2); // after Amount
    });
}





enableColumnDropZones() {
    const table = this.receiptContentRef.el.querySelector(".receipt-table");
    if (!table) return;

    const headers = table.querySelectorAll(
        ".receipt-header-dropzone th"
    );

    headers.forEach((th, index) => {

        // Allow drag
        th.addEventListener("dragover", (ev) => {
            if (ev.dataTransfer.types.includes("application/x-pos-column")) {
                ev.preventDefault(); // REQUIRED
                th.classList.add("column-hover");
            }
        });

        th.addEventListener("dragleave", () => {
            th.classList.remove("column-hover");
        });

        // Handle drop
        th.addEventListener("drop", (ev) => {
            ev.preventDefault();
            th.classList.remove("column-hover");

            const fieldName = ev.dataTransfer.getData(
                "application/x-pos-column"
            );

            if (!fieldName) return;

            this.addColumnAtIndex(fieldName, index);
        });
    });
}

        showPopup(type, x, y, colIndex) {
    this.closePopup();

    this.currentDialog = this.dialog.add(
        this.constructor.components.ColumnCellPopup,
        {
            type,
            colIndex,
            table: this.lastClickedTable,
            cell: this.lastClickedCell,
            x,
            y,
        }
    );
}

closePopup() {
    if (this.currentDialog) {
        this.currentDialog.close();
        this.currentDialog = null;
    }
}


    async getPosConfig() {
        const [config] = await this.orm.searchRead(
            "pos.config",
            [],
            ["id", "selected_product_fields"],
            {limit: 1}
        );
        return config;
    }

    async loadPosConfigId() {
    if (!this.receipt_id) {
        this.notification.add(
            "Receipt ID not found. Please open this from a receipt record.",
            { type: "danger" }
        );
        return;
    }

    const configs = await this.orm.searchRead(
        "pos.config",
        [["receipt_design_id", "=", this.receipt_id]],
        ["id"],
        { limit: 1 }
    );

    const config = configs[0];

    if (!config) {
        this.notification.add(
            "POS Config not found for this receipt. Please link a POS configuration.",
            { type: "warning" }
        );
        return;
    }

    this.config_id = config.id;
    console.log("POS CONFIG ID:", this.config_id);
}


    async loadEnableQr() {
    const [config] = await this.orm.read(
        "pos.config",
        [this.config_id],
        ["enable_qr", "enable_qr_section"]
    );

    this.state.enableQr = !!config.enable_qr;
    this.state.showSection = !!config.enable_qr_section;

    console.log("Loaded enable_qr:", this.state.enableQr);
    console.log("Loaded enable_qr_section:", this.state.showSection);
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

    async allowSpace() {
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

    async loadReceipt(reset = false) {
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
        } else {
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
            await this.orm.write("pos.receipt", [this.receipt_id], {logo: base64});
            this.state.logo = base64;
            await this.loadReceipt();
            this.notification.add("Receipt Logo Updated!", {
                type: "success",
            });
        };
        reader.readAsDataURL(file);
    }

    async saveEditedReceipt() {
        this.state.receipt = this.receiptContentRef.el.innerHTML;
        this.state.prev_logo = this.state.logo;
        this.state.prev_receipt = this.state.receipt;

        await this.orm.write("pos.receipt", [this.receipt_id], {
            design_receipt: this.state.receipt,
            design_receipt_font_style: this.state.fontStyle,
            logo: this.state.logo,
        });

        await this.orm.write("pos.config", [this.config_id], {
            enable_qr: !!this.state.enableQr,
            enable_qr_section: !!this.state.showSection,
        });

        this.notification.add("Receipt Successfully Updated!", {
            type: "success",
        });

        setTimeout(() => window.location.reload(), 800);
    }


    async resetEditedReceipt() {
        if (this.state.prev_receipt) {
            this.state.receipt = this.state.prev_receipt;
            this.receiptContentRef.el.innerHTML = this.state.receipt;
        }
        await this.loadReceipt(true);
        this.notification.add(" Receipt Reset Completed!", {
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
        ghost.style.background = "#000000";
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


    if (ev.dataTransfer.types.includes("application/x-pos-column")) {
        return;
    }
    if (ev.target.closest(".no-drop-zone, .receipt-header")) {
        console.warn("Drop blocked in receipt header");
        return;
    }

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
    } else {
        const targetArea = editor.querySelector(".drop-area");
        if (targetArea) {
            targetArea.appendChild(span);
        }
    }

    this.receiptContentRef.el.classList.remove("dragging");
    this.receiptContentRef.el.classList.remove("drop-highlight");

    span.classList.add("added");
    setTimeout(() => span.classList.remove("added"), 400);
}


    onColumnDragStart(ev) {
    ev.stopPropagation();
    ev.dataTransfer.setData(
        "application/x-pos-column",
        ev.target.dataset.field
    );
    ev.dataTransfer.effectAllowed = "copy";
    this.receiptContentRef.el.classList.add("column-dragging");
}
// addColumnAtIndex(fieldName, index) {
//     const table = this.receiptContentRef.el.querySelector(".receipt-table");
//     if (!table) return;
//
//     const headerRow = table.querySelector("thead tr");
//
//     if (headerRow.querySelector(`[data-field="${fieldName}"]`)) {
//         this.notification.add("Column already added", { type: "warning" });
//         return;
//     }
//
//     if (headerRow.querySelectorAll("th[data-field]").length >= 1) {
//         this.notification.add("Only one column is allowed", { type: "warning" });
//         return;
//     }
//
//     const th = document.createElement("th");
//     th.dataset.field = fieldName;
//     th.textContent = fieldName.replaceAll("_", " ").toUpperCase();
//     th.style.textAlign = "center";
//     th.style.width = "15%";
//
//     headerRow.insertBefore(th, headerRow.children[index + 1] || null);
//
//     this.saveSelectedColumns();
//
//     // Re-render designer preview
//     this.render();
// }




addColumnAtIndex(fieldName, index) {
    const table = this.receiptContentRef.el.querySelector(".receipt-table");
    if (!table) return;

    const headerRow = table.querySelector("thead tr");
    const bodyRows = table.querySelectorAll("tbody tr");

    /* ❌ Prevent duplicate header */
    if (headerRow.querySelector(`[data-field="${fieldName}"]`)) {
        this.notification.add("Column already added", { type: "warning" });
        return;
    }


    const existingDynamicColumns = headerRow.querySelectorAll("th[data-field]");
    if (existingDynamicColumns.length >= 1) {
        this.notification.add(
            "Only one additional column is allowed. Please remove the existing column first.",
            { type: "warning" }
        );
        return;
    }

    const th = document.createElement("th");
    th.dataset.field = fieldName;
    th.textContent = fieldName
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase());

    th.style.textAlign = "center";
    th.style.width = "15%";
    th.style.padding = "4px";
    th.style.whiteSpace = "nowrap";
    th.style.fontFamily = "inherit";


    headerRow.insertBefore(th, headerRow.children[index + 1] || null);

    const lines =
        this.props.lines ||
        this.props.order?.get_orderlines?.() ||
        [];

    bodyRows.forEach((row, rowIndex) => {
        if (row.querySelector(`td[data-field="${fieldName}"]`)) return;

        const td = document.createElement("td");
        td.dataset.field = fieldName;
        td.style.padding = "4px";
        td.style.textAlign = "center";
        td.style.width = "15%";
        td.style.whiteSpace = "nowrap";
        td.style.verticalAlign = "top";
        td.style.fontFamily = "inherit";


        const span = document.createElement("span");
        span.className = "dynamic-cell";
        span.style.display = "inline-block";
        span.style.width = "100%";
        span.style.textAlign = "center";
        span.style.fontFamily = "inherit";

        const line = lines[rowIndex];
        let value = "";

        if (line && line._dynamicValues && fieldName in line._dynamicValues) {
            value = line._dynamicValues[fieldName];
        }

        span.textContent = value || "";
        td.appendChild(span);
        row.insertBefore(td, row.children[index + 1] || null);
    });

    this.saveSelectedColumns();
}

saveSelectedColumns() {
    const table = this.receiptContentRef.el.querySelector(".receipt-table");
    if (!table) return;

    const headerRow = table.querySelector("thead tr");
    if (!headerRow) return;

    const fields = [];

    [...headerRow.children].forEach(th => {
        const field = th.dataset.field;
        if (field) {
            fields.push(field);
        }
    });

    this.selectedProductFields = fields;

    if (this.receipt_id) {
        this.orm.write("pos.receipt", [this.receipt_id], {
            selected_product_fields: JSON.stringify(fields),
        });
    }

    console.log("Saved receipt columns:", fields);
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
    if (!this.state.showSection) return;

    const value = this.inputRef.el?.value?.trim();
    if (!value) {
        this.notification.add("Please enter a value!", { type: "warning" });
        return;
    }

    const editor = this.receiptContentRef.el;
    const targetArea = editor?.querySelector(".qrArea");
    if (!targetArea) return;

    // ❌ DO NOT touch receipt QR
    targetArea.querySelector(".custom-qr-placeholder")?.remove();

    const qrDiv = document.createElement("div");
    qrDiv.className = "custom-qr-placeholder";
    qrDiv.style.textAlign = "center";

    const qrBox = document.createElement("div");
    qrDiv.appendChild(qrBox);
    targetArea.appendChild(qrDiv);

    new QRCode(qrBox, {
        text: value,
        width: 120,
        height: 120,
    });
}


onToggleQr(ev) {
    const checked = ev.target.checked;
    const editor = this.receiptContentRef.el;
    const target = editor?.querySelector(".qrArea");

    if (!checked) {
        target?.querySelector(".custom-qr-placeholder")?.remove();
        return;
    }

    this.submitValue(); // recreate URL QR
}



onToggleReceiptQr(ev) {
    this.state.enableQr = ev.target.checked;

    const editor = this.receiptContentRef.el;
    const wrapper = editor?.querySelector(".receipt-qr-wrapper");
    if (!wrapper) return;

    wrapper.querySelector(".receipt-qr-placeholder")?.remove();

    if (this.state.enableQr) {
        this.renderReceiptQr();
    }
}


   async onReceiptClick(ev) {
    if (this.receiptContentRef.el.classList.contains("column-dragging")) {
        return;
    }

    const table = ev.target.closest("table");
    if (!table) return;

    const th = ev.target.closest("th");
    if (!th) return;

    const colIndex = Array.from(th.parentNode.children).indexOf(th);
    const fieldName = th?.dataset?.field;

    if (!fieldName || colIndex < 3) {
        this.notification.add("Cannot remove this column.", {type: "warning"});
        return;
    }

    this.lastClickedTable = table;
    this.lastClickedColumnIndex = colIndex;

    this.dialog.add(ConfirmationDialog, {
        title: "Remove Column",
        body: `Remove column "${fieldName}"?`,
        confirm: () => this.onRemoveColumnClick(colIndex),
        cancel: () => {},
    });
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
            this.notification.add("Please select a field.", {type: "warning"});
            return;
        }
        if (!this.lastClickedTable) {
            this.notification.add("Click a table first.", {type: "danger"});
            return;
        }
        if (!this.receipt_id) {
            this.notification.add("Receipt ID not found", {type: "danger"});
            return;
        }

        const table = this.lastClickedTable;
        let headerRow = table.querySelector("thead tr") || table.querySelector("tr");
        if (!headerRow) return;

        let bodyRows = table.querySelectorAll("tbody tr");
        if (!bodyRows.length) {
            bodyRows = Array.from(table.querySelectorAll("tr")).slice(1);
        }

        const insertIndex = headerRow.children.length;

        const fieldObj = this.state.productFields.find(f => f.name === fieldName);
        const label = fieldObj?.label || fieldName;

        if (!this.selectedProductFields.includes(fieldName)) {
            this.selectedProductFields.push(fieldName);
        }

        const th = document.createElement("th");
        th.textContent = label;
        th.setAttribute("data-field", fieldName);
        headerRow.appendChild(th);   // end

        bodyRows.forEach((row) => {
            const td = document.createElement("td");
            td.setAttribute("data-field", fieldName);
            td.style.padding = "4px";

            const span = document.createElement("span");
            // span.textContent = `[[ orderline.${fieldName} ]]`;
            // span.setAttribute("t-esc", `orderline.${fieldName}`);

            td.appendChild(span);
            row.appendChild(td);
        });

        await this.orm.write("pos.receipt", [this.receipt_id], {
            selected_product_fields: JSON.stringify(this.selectedProductFields),
        });

        console.log("Saved fields:", this.selectedProductFields);
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

        const selectedFields = this.extractFieldsFromDesign(updatedDesign);

        this.orm
            .call('pos.receipt', 'write', [[this.receipt_id], {
                design_receipt: updatedDesign,
                selected_product_fields: JSON.stringify(selectedFields),
            }])
            .then(() => {
                this.notification.add("Design saved successfully!", {type: "success"});
            })
            .catch((error) => {
                console.error("Save error:", error);
                this.notification.add("Failed to save", {type: "danger"});
            });
    }

    extractFieldsFromDesign(html) {
        const fields = new Set();
        const regex = /\[\[\s*orderline\.([\w_]+)\s*\]\]/g;
        let match;

        while ((match = regex.exec(html)) !== null) {
            fields.add(match[1]);
        }

        return Array.from(fields);
    }

  async onRemoveColumnClick(colIndex = null) {
    if (!this.lastClickedTable) {
        this.notification.add("No table selected.", { type: "danger" });
        return;
    }

    const table = this.lastClickedTable;
    const theadRow = table.querySelector("thead tr");
    const bodyRows = table.querySelectorAll("tbody tr");

    const STATIC_COL_COUNT = 3;
    const columnIndex = colIndex ?? this.lastClickedColumnIndex;

    if (columnIndex == null || columnIndex < STATIC_COL_COUNT) {
        this.notification.add("You cannot remove default columns.", { type: "warning" });
        return;
    }

    const th = theadRow.children[columnIndex];
    const fieldName = th?.dataset?.field;
    if (!fieldName) return;


    const [receipt] = await this.orm.searchRead(
        "pos.receipt",
        [["id", "=", this.receipt_id]],
        ["selected_product_fields"],
        { limit: 1 }
    );

    let fields = JSON.parse(receipt?.selected_product_fields || "[]");
    fields = fields.filter(f => f !== fieldName);

    await this.orm.write("pos.receipt", [this.receipt_id], {
        selected_product_fields: JSON.stringify(fields),
    });


    th.remove();
    bodyRows.forEach(row => row.children[columnIndex]?.remove());


    const lines = this.props.order?.get_orderlines?.() || this.props.lines || [];

    lines.forEach(line => {
        if (line._dynamicValues) {
            delete line._dynamicValues[fieldName];
        }
    });

    this.notification.add(`Column "${fieldName}" removed`, { type: "success" });

    this.lastClickedTable = null;
    this.lastClickedColumnIndex = null;
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