/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { _t } from "@web/core/l10n/translation";

// ── Band colour helpers ──────────────────────────────────────────────────────

const BANDS = [
    { min: 15, bg: "rgba(139,0,0,0.75)",   text: "#fff", label: "Extreme" },
    { min: 8,  bg: "rgba(217,83,79,0.75)", text: "#fff", label: "High" },
    { min: 4,  bg: "rgba(240,173,78,0.75)",text: "#333", label: "Moderate" },
    { min: 1,  bg: "rgba(92,184,92,0.75)", text: "#fff", label: "Low" },
];

function bandBg(c, l) {
    const score = c * l;
    for (const b of BANDS) if (score >= b.min) return b;
    return BANDS[BANDS.length - 1];
}

// ── Custom Pivot Renderer with NHS heat-map coloring ─────────────────────────

class NhsRiskHeatmapPivotRenderer extends PivotRenderer {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._colorize());
        onPatched(() => this._colorize());
    }

    /**
     * After every render, apply NHS risk-band background colours
     * to each data cell based on its consequence and likelihood values.
     */
    _colorize() {
        const table = this.tableRef.el;
        if (!table) return;

        const rows = this.table?.rows || [];
        const trs = [...table.querySelectorAll("tbody tr")];

        trs.forEach((tr, rowIndex) => {
            const rowData = rows[rowIndex];
            if (!rowData) return;

            const tds = [...tr.querySelectorAll("td")];
            tds.forEach((td, colIndex) => {
                const cellData = rowData.subGroupMeasurements?.[colIndex];
                if (!cellData) return;

                 // Extract consequence (row) and likelihood (col) from the cell's group values
                const rowValues = cellData.groupId?.[0] || [];
                const colValues = cellData.groupId?.[1] || [];

                const cValRaw = rowValues[rowValues.length - 1];
                let lValRaw = colValues[colValues.length - 1];

                // If it is the Total column (colValues is empty), find the unique likelihood of active columns
                if (!lValRaw && rowValues.length > 0) {
                    const siblingCells = rowData.subGroupMeasurements || [];
                    const activeLikelihoods = siblingCells
                        .map(c => c.groupId?.[1]?.[c.groupId?.[1]?.length - 1])
                        .filter(l => l !== undefined && l !== null && l !== "");
                    
                    const uniqueLikelihoods = [...new Set(activeLikelihoods)];
                    if (uniqueLikelihoods.length === 1) {
                        lValRaw = uniqueLikelihoods[0];
                    }
                }

                const cVal = parseInt(cValRaw, 10);
                const lVal = parseInt(lValRaw, 10);

                if (!isNaN(cVal) && !isNaN(lVal) && cVal >= 1 && cVal <= 5 && lVal >= 1 && lVal <= 5) {
                    const band = bandBg(cVal, lVal);
                    td.classList.remove("bg-100");
                    td.style.setProperty("background-color", band.bg, "important");
                    td.style.setProperty("color", band.text, "important");
                    td.style.setProperty("font-weight", "600", "important");
                    td.style.setProperty("text-align", "center", "important");
                } else {
                    td.style.removeProperty("background-color");
                    td.style.removeProperty("color");
                    td.style.removeProperty("font-weight");
                    td.style.removeProperty("text-align");
                }
            });
        });
    }
}
NhsRiskHeatmapPivotRenderer.template = PivotRenderer.template;

// ── Custom Pivot Model that forces Total column and custom titles ────────────

class NhsRiskHeatmapPivotModel extends PivotModel {
    _getTableHeaders() {
        const colGroupBys = this.metaData.fullColGroupBys;
        const height = colGroupBys.length + 1;
        const measureCount = this.metaData.activeMeasures.length;
        const leafCounts = this._getLeafCounts(this.data.colGroupTree);
        let headers = [];
        const measureColumns = [];

        const colGroupRows = new Array(height).fill(0).map(() => []);
        colGroupRows[0].push({
            height: height + 1,
            title: "",
            width: 1,
        });

        function generateTreeHeaders(tree, fields) {
            const group = tree.root;
            const rowIndex = group.values.length;
            const row = colGroupRows[rowIndex];
            const groupId = [[], group.values];
            const isLeaf = !tree.directSubTrees.size;
            const leafCount = leafCounts[JSON.stringify(tree.root.values)];
            
            let title = group.labels.length ? group.labels[group.labels.length - 1] : _t("Total");
            
            if (rowIndex > 0) {
                const gbSpec = colGroupBys[rowIndex - 1];
                const fieldName = gbSpec ? gbSpec.split(":")[0] : null;
                if (fieldName === "current_likelihood" && title !== _t("Total") && !String(title).startsWith("Likelihood")) {
                    title = `Likelihood ${title}`;
                }
            }

            const cell = {
                groupId: groupId,
                height: isLeaf ? colGroupBys.length + 1 - rowIndex : 1,
                isLeaf: isLeaf,
                isFolded: isLeaf && colGroupBys.length > group.values.length,
                label:
                    rowIndex === 0
                        ? undefined
                        : fields[colGroupBys[rowIndex - 1].split(":")[0]].string,
                title: title,
                width: leafCount * measureCount,
            };
            row.push(cell);
            if (isLeaf) {
                measureColumns.push(cell);
            }

            [...tree.directSubTrees.values()].forEach((subTree) => {
                generateTreeHeaders(subTree, fields);
            });
        }

        generateTreeHeaders(this.data.colGroupTree, this.metaData.fields);
        
        // Force Total column to always be present by changing > 1 to >= 1
        if (leafCounts[JSON.stringify(this.data.colGroupTree.root.values)] >= 1) {
            var groupId = [[], []];
            var totalTopRightCell = {
                groupId: groupId,
                height: height,
                title: _t("Total"),
                width: measureCount,
            };
            colGroupRows[0].push(totalTopRightCell);
            measureColumns.push(totalTopRightCell);
        }
        headers = headers.concat(colGroupRows);

        var measuresRow = this._getMeasuresRow(measureColumns);
        headers.push(measuresRow);

        return headers;
    }

    _getTableRows(tree, columns) {
        const rows = super._getTableRows(tree, columns);
        const rowGroupBys = this.metaData.fullRowGroupBys;
        rows.forEach((row) => {
            const indent = row.indent;
            if (indent > 0) {
                const gbSpec = rowGroupBys[indent - 1];
                const fieldName = gbSpec ? gbSpec.split(":")[0] : null;
                if (fieldName === "current_consequence" && row.title !== _t("Total") && !String(row.title).startsWith("Consequence")) {
                    row.title = `Consequence ${row.title}`;
                }
            }
        });
        return rows;
    }
}

// ── Custom Pivot View that uses our coloured renderer ────────────────────────

const nhsRiskHeatmapPivotView = {
    ...pivotView,
    Renderer: NhsRiskHeatmapPivotRenderer,
    Model: NhsRiskHeatmapPivotModel,
};

registry.category("views").add("nhs_risk_heatmap_pivot", nhsRiskHeatmapPivotView);

// ── Standalone 5×5 OWL heatmap (client action) ──────────────────────────────

export class RiskHeatmapAction extends Component {
    static template = "odoo_nhs_incident_risk.RiskHeatmap";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");
        this.state  = useState({ grid: {}, loading: true });
        onWillStart(() => this._loadData());
    }

    async _loadData() {
        const risks = await this.orm.searchRead(
            "nhs.risk",
            [["state", "in", ["draft", "active"]]],
            ["current_consequence", "current_likelihood"],
        );
        const grid = {};
        for (const r of risks) {
            const c = r.current_consequence;
            const l = r.current_likelihood;
            if (!c || !l) continue;
            if (!grid[c]) grid[c] = {};
            grid[c][l] = (grid[c][l] || 0) + 1;
        }
        this.state.grid    = grid;
        this.state.loading = false;
    }

    getCount(c, l) {
        return (this.state.grid[String(c)] || {})[String(l)] || 0;
    }

    getCellBg(c, l) { return bandBg(c, l).bg; }

    async onCellClick(ev) {
        const td = ev.target.closest("td[data-c]");
        if (!td) return;
        const c = td.dataset.c;
        const l = td.dataset.l;
        if (!this.getCount(c, l)) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: `Risks — C${c} × L${l}`,
            res_model: "nhs.risk",
            view_mode: "list,form",
            domain: [
                ["state", "in", ["draft", "active"]],
                ["current_consequence", "=", c],
                ["current_likelihood", "=", l],
            ],
        });
    }

    get consequences() { return [5, 4, 3, 2, 1]; }
    get likelihoods()  { return [1, 2, 3, 4, 5]; }
    get bands()        { return BANDS; }
}

registry.category("actions").add("nhs_risk_heatmap", RiskHeatmapAction);
