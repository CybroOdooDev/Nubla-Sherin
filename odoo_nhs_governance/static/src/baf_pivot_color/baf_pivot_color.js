/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

const BAF_RISK_MODEL = "nhs.baf.risk";
const BAF_SCORE_MEASURES = ["current_score", "target_score"];

function scoreToColor(score) {
    if (score >= 15) {
        return "#c62828"; // extreme
    }
    if (score >= 8) {
        return "#ef6c00"; // high
    }
    if (score >= 4) {
        return "#f9a825"; // moderate
    }
    if (score >= 1) {
        return "#2e7d32"; // low
    }
    return null;
}

patch(PivotRenderer.prototype, {
    getBafCellStyle(cell) {
        const resModel = this.model.metaData.resModel;
        if (
            resModel !== BAF_RISK_MODEL ||
            cell.value === undefined ||
            !BAF_SCORE_MEASURES.includes(cell.measure)
        ) {
            return "";
        }
        const color = scoreToColor(Number(cell.value));
        if (!color) {
            return "";
        }
        return `background-color: ${color} !important; color: #ffffff !important;`;
    },
});
