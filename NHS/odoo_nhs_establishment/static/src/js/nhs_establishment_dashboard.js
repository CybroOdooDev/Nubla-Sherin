/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NhsEstablishmentDashboardAction extends Component {
    static template = "odoo_nhs_establishment.EstablishmentDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            summary: { funded: 0, in_post: 0, vacant: 0, rate: 0 },
            staffGroups: [],
            bands: [],
            hotspots: [],
            payBudgets: [],
            costCentres: [],
        });
        onWillStart(() => this._loadData());
    }

    async _loadData() {
        this.state.loading = true;
        // Load all active posts
        const posts = await this.orm.searchRead(
            "nhs.establishment.post",
            [["status", "in", ["active", "frozen"]]],
            ["funded_fte", "in_post_fte", "vacant_fte", "staff_group_id", "band_id", "org_unit_id", "is_medical", "indicative_pay"]
        );

        // Load vacancy hotspots from org units
        const hotspots = await this.orm.searchRead(
            "nhs.org.unit",
            [["funded_fte", ">", 0]],
            ["name", "complete_name", "funded_fte", "in_post_fte", "vacant_fte", "vacancy_rate", "manager_id"],
            { order: "vacancy_rate desc", limit: 5 }
        );

        // Load cost-centre budgets, worst utilisation first
        const costCentres = await this.orm.searchRead(
            "nhs.cost.centre",
            [["budget_amount", ">", 0]],
            ["name", "code", "budget_amount", "indicative_pay_total", "budget_variance", "budget_utilization"],
            { order: "budget_utilization desc", limit: 5 }
        );

        // Process summary
        let totalFunded = 0;
        let totalInPost = 0;
        let totalVacant = 0;
        
        // Grouping maps
        const grpMap = {};
        const bandMap = {};
        const areaMap = {};

        for (const p of posts) {
            totalFunded += p.funded_fte || 0.0;
            totalInPost += p.in_post_fte || 0.0;
            totalVacant += p.vacant_fte || 0.0;

            // Staff Group
            const grpName = p.staff_group_id ? p.staff_group_id[1] : "Undefined";
            if (!grpMap[grpName]) grpMap[grpName] = { name: grpName, funded: 0, in_post: 0, vacant: 0 };
            grpMap[grpName].funded += p.funded_fte || 0.0;
            grpMap[grpName].in_post += p.in_post_fte || 0.0;
            grpMap[grpName].vacant += p.vacant_fte || 0.0;

            // Band
            let bandName = "No Band";
            if (p.is_medical) {
                bandName = "Medical / Non-AfC";
            } else if (p.band_id) {
                bandName = p.band_id[1];
            }
            if (!bandMap[bandName]) bandMap[bandName] = { name: bandName, funded: 0, in_post: 0, vacant: 0 };
            bandMap[bandName].funded += p.funded_fte || 0.0;
            bandMap[bandName].in_post += p.in_post_fte || 0.0;
            bandMap[bandName].vacant += p.vacant_fte || 0.0;

            // Area Pay Budget
            const areaName = p.org_unit_id ? p.org_unit_id[1] : "General";
            if (!areaMap[areaName]) areaMap[areaName] = { name: areaName, budget: 0 };
            areaMap[areaName].budget += p.indicative_pay || 0.0;
        }

        // Finalize Staff Groups array
        const staffGroups = Object.values(grpMap).map(g => {
            const rate = g.funded > 0 ? (g.vacant / g.funded) * 100 : 0;
            return { ...g, rate: Math.max(0, Math.min(100, rate)) };
        }).sort((a, b) => b.funded - a.funded);

        // Finalize Bands array
        const bands = Object.values(bandMap).map(b => {
            const rate = b.funded > 0 ? (b.vacant / b.funded) * 100 : 0;
            return { ...b, rate: Math.max(0, Math.min(100, rate)) };
        }).sort((a, b) => b.funded - a.funded);

        // Finalize Pay Budgets array
        const payBudgets = Object.values(areaMap)
            .sort((a, b) => b.budget - a.budget)
            .slice(0, 5);

        this.state.summary = {
            funded: totalFunded,
            in_post: totalInPost,
            vacant: totalVacant,
            rate: totalFunded > 0 ? (totalVacant / totalFunded) * 100 : 0
        };
        this.state.staffGroups = staffGroups;
        this.state.bands = bands;
        this.state.hotspots = hotspots.map(h => {
            return {
                ...h,
                vacancy_rate: (h.vacancy_rate || 0) * 100
            };
        });
        this.state.payBudgets = payBudgets;
        this.state.costCentres = costCentres.map(cc => ({
            ...cc,
            budget_utilization: (cc.budget_utilization || 0) * 100,
        }));
        this.state.loading = false;
    }

    async refresh() {
        await this._loadData();
    }

    formatFTE(val) {
        return (val || 0).toFixed(2);
    }

    formatPercent(val) {
        return (val || 0).toFixed(1) + "%";
    }

    formatCurrency(val) {
        return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(val || 0);
    }

    async openDetails(viewName, resModel, domain = [], context = {}) {
        const viewTypes = "pivot_row_groupby" in context || "pivot_measures" in context
            ? ["pivot", "list"]
            : ["list", "form"];
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: viewName,
            res_model: resModel,
            views: viewTypes.map((v) => [false, v]),
            view_mode: viewTypes.join(","),
            domain: domain,
            context: context,
        });
    }

    async openHotspot(hotspot) {
        await this.openDetails(
            `Posts for ${hotspot.name}`,
            "nhs.establishment.post",
            [["org_unit_id", "child_of", hotspot.id], ["status", "in", ["active", "frozen"]]]
        );
    }

    async openCostCentre(costCentre) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: costCentre.name,
            res_model: "nhs.cost.centre",
            views: [[false, "form"]],
            res_id: costCentre.id,
        });
    }
}

registry.category("actions").add("nhs_establishment_dashboard", NhsEstablishmentDashboardAction);
