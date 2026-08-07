/** @odoo-module **/

import { Component, onWillStart, useState, useEffect, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

export class NhsComplianceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
            activeRemedialTab: "failed",
            failedTestsCount: 0,
            overdueItems: [],
            dueSoonItems: [],
            failedTests: [],
            openRemedials: [],
            buildings: [],
        });

        // Refs for the 4 charts
        this.disciplineChartRef = useRef("disciplineChart");
        this.siteChartRef = useRef("siteChart");
        this.buildingChartRef = useRef("buildingChart");
        this.trendChartRef = useRef("trendChart");

        this.chartInstances = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            
            // 1. Fetch baseline compliance metrics from python
            this.state.metrics = await this.orm.call("nhs.compliance.item", "get_compliance_dashboard_metrics", []);
            
            // 2. Fetch all buildings for Site/Building mappings
            this.state.buildings = await this.orm.searchRead("nhs.estate.building", [], ["id", "name", "site_id"]);
            
            // 3. Fetch failed tests count for KPI
            this.state.failedTestsCount = await this.orm.searchCount("nhs.compliance.test", [["outcome", "in", ["fail", "remedial_required"]]]);
            
            // 4. Fetch latest 3 overdue items
            this.state.overdueItems = await this.orm.searchRead(
                "nhs.compliance.item",
                [["status", "=", "overdue"]],
                ["id", "reference", "name", "next_due_date"],
                { limit: 3, order: "next_due_date asc" }
            );

            // 5. Fetch latest 3 due soon items
            this.state.dueSoonItems = await this.orm.searchRead(
                "nhs.compliance.item",
                [["status", "=", "due_soon"]],
                ["id", "reference", "name", "next_due_date"],
                { limit: 3, order: "next_due_date asc" }
            );

            // 6. Fetch latest 3 failed tests
            this.state.failedTests = await this.orm.searchRead(
                "nhs.compliance.test",
                [["outcome", "in", ["fail", "remedial_required"]]],
                ["id", "name", "item_id", "test_date", "outcome"],
                { limit: 3, order: "test_date desc" }
            );

            // 7. Fetch latest 3 open/in-progress remedials
            this.state.openRemedials = await this.orm.searchRead(
                "nhs.compliance.remedial",
                [["state", "in", ["open", "in_progress"]]],
                ["id", "name", "item_id", "priority", "due_date"],
                { limit: 3, order: "due_date asc" }
            );

            this.state.loading = false;
        });

        useEffect(() => {
            if (!this.state.loading) {
                this.renderCharts();
            }
        }, () => [this.state.loading]);

        onWillUnmount(() => {
            Object.values(this.chartInstances).forEach(chart => {
                if (chart) chart.destroy();
            });
        });
    }

    setOpsTab(tabName) {
        this.state.activeRemedialTab = tabName;
    }

    renderCharts() {
        const metrics = this.state.metrics;

        // Destroy existing chart instances to avoid canvas reuse errors
        Object.values(this.chartInstances).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.chartInstances = {};

        const labelFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 11,
            weight: 'normal'
        };

        const titleFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 12,
            weight: 'bold'
        };

        // 1. Compliance by Discipline Chart (Horizontal Bar Chart for readability)
        if (this.disciplineChartRef.el) {
            const disciplineStats = {};
            if (metrics.rag_matrix) {
                metrics.rag_matrix.forEach(row => {
                    row.cells.forEach(cell => {
                        if (cell.total > 0) {
                            const name = cell.discipline_name;
                            if (!disciplineStats[name]) {
                                disciplineStats[name] = { total: 0, compliant: 0 };
                            }
                            disciplineStats[name].total += cell.total;
                            const compliantCount = (cell.rate * cell.total) / 100;
                            disciplineStats[name].compliant += compliantCount;
                        }
                    });
                });
            }

            const disciplineLabels = [];
            const disciplineData = [];
            Object.entries(disciplineStats).forEach(([name, stats]) => {
                disciplineLabels.push(name);
                disciplineData.push(stats.total > 0 ? Math.round((stats.compliant / stats.total) * 100) : 0);
            });

            this.chartInstances.discipline = new window.Chart(this.disciplineChartRef.el, {
                type: 'bar',
                data: {
                    labels: disciplineLabels,
                    datasets: [{
                        label: 'Compliance %',
                        data: disciplineData,
                        backgroundColor: '#005EB8',
                        borderRadius: 4,
                        maxBarThickness: 25
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: (context) => ` Compliance: ${context.raw}%`
                            }
                        }
                    },
                    scales: {
                        x: {
                            min: 0,
                            max: 100,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFontConfig, callback: (value) => `${value}%` }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }

        // 2. Compliance by Site (Line Chart)
        if (this.siteChartRef.el && metrics.site_compliance) {
            const siteLabels = metrics.site_compliance.map(s => s.name);
            const siteData = metrics.site_compliance.map(s => s.rate);

            this.chartInstances.site = new window.Chart(this.siteChartRef.el, {
                type: 'line',
                data: {
                    labels: siteLabels,
                    datasets: [{
                        label: 'Compliance %',
                        data: siteData,
                        borderColor: '#005EB8',
                        backgroundColor: 'rgba(0, 94, 184, 0.1)',
                        borderWidth: 2.5,
                        tension: 0.3,
                        pointBackgroundColor: '#005EB8',
                        pointBorderColor: '#fff',
                        pointRadius: 4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: (context) => ` Compliance: ${context.raw}%`
                            }
                        }
                    },
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFontConfig, callback: (value) => `${value}%` }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }

        // 3. Compliance by Building (Pie Chart)
        if (this.buildingChartRef.el) {
            const buildingLabels = [];
            const buildingData = [];
            if (metrics.rag_matrix) {
                metrics.rag_matrix.forEach(row => {
                    let total = 0;
                    let compliant = 0;
                    row.cells.forEach(cell => {
                        if (cell.total > 0) {
                            total += cell.total;
                            const compliantCount = (cell.rate * cell.total) / 100;
                            compliant += compliantCount;
                        }
                    });
                    if (total > 0) {
                        buildingLabels.push(row.building_name);
                        buildingData.push(Math.round((compliant / total) * 100));
                    }
                });
            }

            const palette = ['#005EB8', '#41B6E6', '#00A3A6', '#009639', '#FFB81C', '#DA291C', '#78BE20', '#7C2F8A'];
            const bgColors = buildingLabels.map((_, i) => palette[i % palette.length]);

            this.chartInstances.building = new window.Chart(this.buildingChartRef.el, {
                type: 'pie',
                data: {
                    labels: buildingLabels,
                    datasets: [{
                        label: 'Compliance %',
                        data: buildingData,
                        backgroundColor: bgColors,
                        borderWidth: 1.5,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'right',
                            labels: { font: labelFontConfig }
                        },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: (context) => ` ${context.label}: ${context.raw}%`
                            }
                        }
                    }
                }
            });
        }

        // 4. Month-on-Month Compliance Trend (Vertical Bar Chart)
        if (this.trendChartRef.el && metrics.trend_over_time) {
            this.chartInstances.trend = new window.Chart(this.trendChartRef.el, {
                type: 'bar',
                data: {
                    labels: metrics.trend_over_time.map(t => t.month),
                    datasets: [
                        {
                            label: 'Completed Tests',
                            data: metrics.trend_over_time.map(t => t.completed),
                            backgroundColor: '#005EB8',
                            borderRadius: 4
                        },
                        {
                            label: 'Overdue Items',
                            data: metrics.trend_over_time.map(t => t.overdue),
                            backgroundColor: '#DA291C',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { font: labelFontConfig }
                        },
                        tooltip: { bodyFont: labelFontConfig }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFontConfig, stepSize: 1 }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }
    }

    openAction(resModel, viewMode = 'list,form', domain = [], context = {}) {
        const views = viewMode.split(',').map(mode => [false, mode]);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Details',
            res_model: resModel,
            views: views,
            domain: domain,
            context: context,
            target: 'current',
        });
    }

    openRecord(resModel, resId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: resModel,
            res_id: resId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openComplianceRate() {
        this.openAction('nhs.compliance.item', 'list,form', [['status', '=', 'compliant']]);
    }

    openTotalAssetsLocations() {
        this.openAction('nhs.compliance.item', 'list,form', [['active', '=', true]]);
    }

    openActiveSchedules() {
        this.openAction('nhs.compliance.item', 'list,form', [['active', '=', true]]);
    }

    openOverdueTests() {
        this.openAction('nhs.compliance.item', 'list,form', [['status', '=', 'overdue']]);
    }

    openDueSoonItems() {
        this.openAction('nhs.compliance.item', 'list,form', [['status', '=', 'due_soon']]);
    }

    openFailedTests() {
        this.openAction('nhs.compliance.test', 'list,form', [['outcome', 'in', ['fail', 'remedial_required']]]);
    }

    openFailedItems() {
        this.openAction('nhs.compliance.item', 'list,form', [['status', '=', 'failed']]);
    }

    openOpenNonCompliance() {
        this.openAction('nhs.compliance.remedial', 'list,form', [['state', 'in', ['open', 'in_progress']]]);
    }

    openExpiringCertificates() {
        const today = new Date();
        const startStr = today.toISOString().slice(0, 10);
        const next30 = new Date(new Date().setDate(today.getDate() + 30)).toISOString().slice(0, 10);
        this.openAction('nhs.compliance.test', 'list,form', [
            ['certificate_expiry', '>=', startStr],
            ['certificate_expiry', '<=', next30]
        ]);
    }

    openCompletedThisMonth() {
        const today = new Date();
        const startStr = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
        const endStr = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().slice(0, 10);
        this.openAction('nhs.compliance.test', 'list,form', [
            ['test_date', '>=', startStr],
            ['test_date', '<=', endStr]
        ]);
    }

    openItem(id) {
        this.openRecord('nhs.compliance.item', id);
    }

    openTest(id) {
        this.openRecord('nhs.compliance.test', id);
    }

    openRemedial(id) {
        this.openRecord('nhs.compliance.remedial', id);
    }
}

NhsComplianceDashboard.template = "odoo_nhs_estate_compliance.NhsComplianceDashboard";

registry.category("actions").add("nhs_compliance_dashboard", NhsComplianceDashboard);
