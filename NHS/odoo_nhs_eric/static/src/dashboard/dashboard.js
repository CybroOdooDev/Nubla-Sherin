/** @odoo-module **/

import { Component, onWillStart, useState, useEffect, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

export class NhsEricDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });

        this.coverageChartRef = useRef("coverageChart");
        this.sectionProgressChartRef = useRef("sectionProgressChart");
        this.trendGiaBacklogChartRef = useRef("trendGiaBacklogChart");
        this.trendCostComplianceChartRef = useRef("trendCostComplianceChart");
        this.chartInstances = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.state.metrics = await this.orm.call("nhs.eric.return", "get_dashboard_metrics", []);
            this.state.loading = false;
        });

        useEffect(() => {
            if (!this.state.loading && this.state.metrics.has_data) {
                this.renderCharts();
            }
        }, () => [this.state.loading, this.state.metrics]);

        onWillUnmount(() => {
            Object.values(this.chartInstances).forEach(chart => {
                if (chart) chart.destroy();
            });
        });
    }

    async onReturnChange(ev) {
        const returnId = parseInt(ev.target.value);
        this.state.loading = true;
        this.state.metrics = await this.orm.call("nhs.eric.return", "get_dashboard_metrics", [returnId]);
        this.state.loading = false;
    }

    renderCharts() {
        const metrics = this.state.metrics;

        // Destroy existing charts
        Object.values(this.chartInstances).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.chartInstances = {};

        const labelFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 11,
            weight: 'bold'
        };

        const titleFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 12,
            weight: 'bold'
        };

        // 1. Data-Source Coverage Doughnut Chart
        if (this.coverageChartRef.el) {
            const coverage = metrics.coverage || {};
            const auto = coverage.auto || 0;
            const manual = coverage.manual || 0;
            const computed = coverage.computed || 0;
            const total = auto + manual + computed;

            this.chartInstances.coverage = new window.Chart(this.coverageChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: ['Auto-sourced', 'Manual Entry', 'Computed'],
                    datasets: [{
                        data: [auto, manual, computed],
                        backgroundColor: ['#005EB8', '#CE7B11', '#009639'],
                        borderWidth: 1.5,
                        borderColor: '#ffffff',
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const types = ['auto', 'manual', 'computed'];
                            const selectedType = types[index];
                            this.openAction('nhs.eric.value', 'list,form', [
                                ['return_id', '=', metrics.selected_return_id],
                                ['item_def_id.source_type', '=', selectedType]
                            ]);
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                boxWidth: 14,
                                padding: 12,
                                font: labelFontConfig
                            }
                        },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed || 0;
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${value} fields (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '55%'
                }
            });
        }

        // 2. Section Completeness Bar Chart
        if (this.sectionProgressChartRef.el && metrics.section_lines) {
            const sections = metrics.section_lines;
            
            this.chartInstances.sectionProgress = new window.Chart(this.sectionProgressChartRef.el, {
                type: 'bar',
                data: {
                    labels: sections.map(s => s.name),
                    datasets: [{
                        label: 'Completeness %',
                        data: sections.map(s => s.completeness_pct),
                        backgroundColor: sections.map(s => {
                            if (s.state === 'signed_off') return '#009639';
                            if (s.state === 'ready_for_review') return '#00A3E0';
                            if (s.state === 'in_progress') return '#CE7B11';
                            return '#768692';
                        }),
                        borderRadius: 4,
                        maxBarThickness: 30
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const sec = sections[index];
                            this.openAction('nhs.eric.value', 'list,form', [
                                ['return_id', '=', metrics.selected_return_id],
                                ['section_id.name', '=', sec.name]
                            ]);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    return ` Completeness: ${context.parsed.x.toFixed(1)}%`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#E8EDEE' },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) { return value + '%'; }
                            }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }

        // 3. YoY GIA & Backlog Trend Chart
        if (this.trendGiaBacklogChartRef.el && metrics.trends && metrics.trends.length > 0) {
            const trends = metrics.trends;
            
            this.chartInstances.trendGiaBacklog = new window.Chart(this.trendGiaBacklogChartRef.el, {
                type: 'bar',
                data: {
                    labels: trends.map(t => t.year),
                    datasets: [
                        {
                            label: 'Total GIA (m²)',
                            data: trends.map(t => t.gia),
                            backgroundColor: '#005EB8',
                            yAxisID: 'yGia',
                            borderRadius: 4,
                            maxBarThickness: 25
                        },
                        {
                            label: 'Backlog Cost (£)',
                            data: trends.map(t => t.backlog),
                            borderColor: '#DA291C',
                            backgroundColor: 'rgba(218, 41, 28, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#DA291C',
                            pointRadius: 4,
                            type: 'line',
                            yAxisID: 'yBacklog',
                            tension: 0.25
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
                        yGia: {
                            type: 'linear',
                            position: 'left',
                            title: {
                                display: true,
                                text: 'GIA (m²)',
                                font: titleFontConfig
                            },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) { return value.toLocaleString() + ' m²'; }
                            },
                            grid: { color: '#E8EDEE' }
                        },
                        yBacklog: {
                            type: 'linear',
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Backlog (£)',
                                font: titleFontConfig
                            },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) {
                                    if (value >= 1000000) return '£' + (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return '£' + (value / 1000).toFixed(0) + 'k';
                                    return '£' + value;
                                }
                            },
                            grid: { display: false }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }

        // 4. YoY Cost per m² & Compliance Trend Chart
        if (this.trendCostComplianceChartRef.el && metrics.trends && metrics.trends.length > 0) {
            const trends = metrics.trends;

            this.chartInstances.trendCostCompliance = new window.Chart(this.trendCostComplianceChartRef.el, {
                type: 'line',
                data: {
                    labels: trends.map(t => t.year),
                    datasets: [
                        {
                            label: 'Cost per m² (£/m²)',
                            data: trends.map(t => t.cost_per_m2),
                            borderColor: '#CE7B11',
                            backgroundColor: 'transparent',
                            borderWidth: 3,
                            pointBackgroundColor: '#CE7B11',
                            pointRadius: 4,
                            yAxisID: 'yCost',
                            tension: 0.2
                        },
                        {
                            label: 'Compliance %',
                            data: trends.map(t => t.compliance_pct),
                            borderColor: '#009639',
                            backgroundColor: 'transparent',
                            borderWidth: 3,
                            pointBackgroundColor: '#009639',
                            pointRadius: 4,
                            yAxisID: 'yComp',
                            tension: 0.2
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
                        yCost: {
                            type: 'linear',
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Cost per m² (£)',
                                font: titleFontConfig
                            },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) { return '£' + value.toFixed(1); }
                            },
                            grid: { color: '#E8EDEE' }
                        },
                        yComp: {
                            type: 'linear',
                            position: 'right',
                            max: 100,
                            title: {
                                display: true,
                                text: 'Compliance %',
                                font: titleFontConfig
                            },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) { return value + '%'; }
                            },
                            grid: { display: false }
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

    openAction(resModel, viewMode = 'list,form', domain = []) {
        const views = viewMode.split(',').map(mode => [false, mode]);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'ERIC Values',
            res_model: resModel,
            views: views,
            domain: domain,
            target: 'current',
        });
    }

    openReturn() {
        if (this.state.metrics.selected_return_id) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'nhs.eric.return',
                res_id: this.state.metrics.selected_return_id,
                views: [[false, 'form']],
                target: 'current',
            });
        }
    }

    openReturnSection(sectionLineId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'nhs.eric.return.section',
            res_id: sectionLineId,
            views: [[false, 'form']],
            target: 'new',
        });
    }
}

NhsEricDashboard.template = "odoo_nhs_eric.NhsEricDashboard";

registry.category("actions").add("nhs_eric_dashboard", NhsEricDashboard);
