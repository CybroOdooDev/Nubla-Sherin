/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ── Band colour helpers ──────────────────────────────────────────────────────

export const BANDS = [
    { min: 15, bg: "rgba(139,0,0,0.75)",   text: "#fff", label: "Extreme" },
    { min: 8,  bg: "rgba(217,83,79,0.75)", text: "#fff", label: "High" },
    { min: 4,  bg: "rgba(240,173,78,0.75)",text: "#333", label: "Moderate" },
    { min: 1,  bg: "rgba(92,184,92,0.75)", text: "#fff", label: "Low" },
];

export function bandBg(c, l) {
    const score = c * l;
    for (const b of BANDS) if (score >= b.min) return b;
    return BANDS[BANDS.length - 1];
}

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

