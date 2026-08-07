/** @odoo-module **/

import { Component, onWillStart, useState, useEffect, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

export class NhsEstateDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });
        this.conditionChartRef = useRef("conditionChart");
        this.backlogRiskChartRef = useRef("backlogRiskChart");
        this.tenureChartRef = useRef("tenureChart");
        this.giaFunctionChartRef = useRef("giaFunctionChart");
        this.leaseExpiryChartRef = useRef("leaseExpiryChart");
        this.operationalStatusChartRef = useRef("operationalStatusChart");
        this.chartInstances = {};
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.state.metrics = await this.orm.call("nhs.estate.site", "get_dashboard_metrics", []);
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

    renderCharts() {
        const metrics = this.state.metrics;
        Object.values(this.chartInstances).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.chartInstances = {};
        const labelFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 12,
            weight: 'bold'
        };
        const titleFontConfig = {
            family: 'Outfit, Inter, sans-serif',
            size: 13,
            weight: 'bold'
        };
        if (this.conditionChartRef.el) {
            const conditionData = metrics.condition_grades || {};
            const gradeA = conditionData['A'] || 0;
            const gradeB = conditionData['B'] || 0;
            const gradeC = conditionData['C'] || 0;
            const gradeD = conditionData['D'] || 0;
            const unassessed = conditionData['False'] || 0;
            const total = gradeA + gradeB + gradeC + gradeD + unassessed;
            this.chartInstances.condition = new window.Chart(this.conditionChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: ['A (Good)', 'B (Satisfactory)', 'C (Poor)', 'D (Very Poor)', 'Unassessed'],
                    datasets: [{
                        data: [gradeA, gradeB, gradeC, gradeD, unassessed],
                        backgroundColor: ['#009639', '#41B6E6', '#CE7B11', '#DA291C', '#768692'],
                        borderWidth: 1.5,
                        borderColor: '#ffffff',
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const grades = ['A', 'B', 'C', 'D', false];
                            const selectedGrade = grades[index];
                            this.openAction('nhs.estate.building', 'list,form', [['latest_condition_grade', '=', selectedGrade]]);
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 16,
                                padding: 14,
                                font: titleFontConfig
                            }
                        },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed || 0;
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
        }
        if (this.backlogRiskChartRef.el) {
            const backlogRisk = metrics.backlog_by_risk || {};
            this.chartInstances.backlogRisk = new window.Chart(this.backlogRiskChartRef.el, {
                type: 'bar',
                data: {
                    labels: ['High', 'Significant', 'Moderate', 'Low'],
                    datasets: [{
                        data: [
                            backlogRisk.high || 0,
                            backlogRisk.significant || 0,
                            backlogRisk.moderate || 0,
                            backlogRisk.low || 0
                        ],
                        backgroundColor: ['#DA291C', '#CE7B11', '#41B6E6', '#009639'],
                        borderRadius: 6,
                        maxBarThickness: 45
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const risks = ['high', 'significant', 'moderate', 'low'];
                            const selectedRisk = risks[index];
                            this.openAction('nhs.estate.backlog', 'list,form', [['risk_category', '=', selectedRisk]]);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    return ` Backlog: £${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) {
                                    if (value >= 1000000) return '£' + (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return '£' + (value / 1000).toFixed(0) + 'k';
                                    return '£' + value;
                                }
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }
        if (this.tenureChartRef.el) {
            const tenureData = metrics.tenure_breakdown || {};
            const labels = ['Freehold', 'Leasehold', 'PFI', 'LIFT', 'NHSPS', 'CHP', 'Licence'];
            const keys = ['freehold', 'leasehold', 'pfi', 'lift', 'nhsps', 'chp', 'licence'];
            const dataCounts = keys.map(k => (tenureData[k] && tenureData[k].count) || 0);
            const totalTenures = dataCounts.reduce((a, b) => a + b, 0);
            this.chartInstances.tenure = new window.Chart(this.tenureChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataCounts,
                        backgroundColor: ['#003087', '#005EB8', '#41B6E6', '#00A3E0', '#330072', '#7C2855', '#768692'],
                        borderWidth: 1.5,
                        borderColor: '#ffffff',
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const tenures = ['freehold', 'leasehold', 'pfi', 'lift', 'nhsps', 'chp', 'licence'];
                            const selectedTenure = tenures[index];
                            this.openAction('nhs.estate.building', 'list,form', [['tenure_type', '=', selectedTenure]]);
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 16,
                                padding: 14,
                                font: titleFontConfig
                            }
                        },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed || 0;
                                    const percentage = totalTenures > 0 ? ((value / totalTenures) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
        }
        if (this.giaFunctionChartRef.el && metrics.gia_by_function) {
            const sortedFunc = [...metrics.gia_by_function]
                .sort((a, b) => b.gia - a.gia)
                .slice(0, 6);
            this.chartInstances.giaFunction = new window.Chart(this.giaFunctionChartRef.el, {
                type: 'bar',
                data: {
                    labels: sortedFunc.map(f => f.name),
                    datasets: [{
                        data: sortedFunc.map(f => f.gia),
                        backgroundColor: '#005EB8',
                        borderRadius: 6,
                        maxBarThickness: 25
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const selectedFunctionName = sortedFunc[index].name;
                            if (selectedFunctionName === 'Unassigned') {
                                this.openAction('nhs.estate.building', 'list,form', [['function_id', '=', false]]);
                            } else {
                                this.openAction('nhs.estate.building', 'list,form', [['function_id.name', '=', selectedFunctionName]]);
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    return ` GIA: ${context.parsed.x.toLocaleString()} m²`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: {
                                font: labelFontConfig,
                                callback: function(value) {
                                    if (value >= 1000) return (value / 1000).toFixed(1) + 'k m²';
                                    return value + ' m²';
                                }
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
        if (this.leaseExpiryChartRef.el && metrics.lease_expiries_by_month) {
            const dataExp = metrics.lease_expiries_by_month;
            this.chartInstances.leaseExpiry = new window.Chart(this.leaseExpiryChartRef.el, {
                type: 'line',
                data: {
                    labels: dataExp.map(d => d.month),
                    datasets: [{
                        label: 'Lease & Contract Expiries',
                        data: dataExp.map(d => d.count),
                        borderColor: '#005EB8',
                        backgroundColor: 'rgba(0, 94, 184, 0.08)',
                        borderWidth: 3,
                        pointBackgroundColor: '#005EB8',
                        pointRadius: 5,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const today = new Date();
                            const startMonth = new Date(today.getFullYear(), today.getMonth() + index, 1);
                            const endMonth = new Date(today.getFullYear(), today.getMonth() + index + 1, 0);
                            const startStr = startMonth.toISOString().slice(0, 10);
                            const endStr = endMonth.toISOString().slice(0, 10);
                            this.openAction('nhs.estate.tenure', 'list,form', [
                                ['lease_end', '>=', startStr],
                                ['lease_end', '<=', endStr]
                            ]);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    return ` Expiries: ${context.parsed.y} contracts`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: {
                                font: labelFontConfig,
                                stepSize: 1
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: labelFontConfig }
                        }
                    }
                }
            });
        }
        if (this.operationalStatusChartRef.el) {
            const opData = metrics.operational_status || {};
            const opTotal = (opData.operational || 0) + (opData.partial || 0) + (opData.closed || 0) + (opData.disposed || 0);
            this.chartInstances.operationalStatus = new window.Chart(this.operationalStatusChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: ['Operational', 'Partially Operational', 'Closed', 'Disposed'],
                    datasets: [{
                        data: [
                            opData.operational || 0,
                            opData.partial || 0,
                            opData.closed || 0,
                            opData.disposed || 0
                        ],
                        backgroundColor: ['#009639', '#CE7B11', '#DA291C', '#768692'],
                        borderWidth: 1.5,
                        borderColor: '#ffffff',
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const index = elements[0].index;
                            const statuses = ['operational', 'partial', 'closed', 'disposed'];
                            const selectedStatus = statuses[index];
                            this.openAction('nhs.estate.building', 'list,form', [['operational_status', '=', selectedStatus]]);
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 16,
                                padding: 14,
                                font: titleFontConfig
                            }
                        },
                        tooltip: {
                            bodyFont: labelFontConfig,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed || 0;
                                    const percentage = opTotal > 0 ? ((value / opTotal) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
        }
    }

    openAction(resModel, viewMode = 'list,form', domain = []) {
        const views = viewMode.split(',').map(mode => [false, mode]);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Details',
            res_model: resModel,
            views: views,
            domain: domain,
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

    openSites() {
        this.openAction('nhs.estate.site', 'list,form', [['active', '=', true]]);
    }
    openBuildings() {
        this.openAction('nhs.estate.building');
    }
    openFloors() {
        this.openAction('nhs.estate.floor');
    }
    openSpaces() {
        this.openAction('nhs.estate.space');
    }
    openBacklogs() {
        this.openAction('nhs.estate.backlog');
    }
    openHighRiskBacklogs() {
        this.openAction('nhs.estate.backlog', 'list,form', [['risk_category', '=', 'high']]);
    }
    openExpiringTenures() {
        const today = new Date().toISOString().slice(0, 10);
        const nextYear = new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10);
        this.openAction('nhs.estate.tenure', 'list,form', [
            '|', '|',
            '&', '&',
                ['lease_end', '!=', false],
                ['lease_end', '>=', today],
                ['lease_end', '<=', nextYear],
            '&', '&',
                ['contract_end', '!=', false],
                ['contract_end', '>=', today],
                ['contract_end', '<=', nextYear],
            '&', '&',
                ['break_date', '!=', false],
                ['break_date', '>=', today],
                ['break_date', '<=', nextYear]
        ]);
    }
    openConditionDBuildings() {
        this.openAction('nhs.estate.building', 'list,form', [['latest_condition_grade', '=', 'D']]);
    }

    openOverdueSurveys() {
        const today = new Date().toISOString().slice(0, 10);
        this.openAction('nhs.estate.condition', 'list,form', [
            ['next_survey_date', '!=', false],
            ['next_survey_date', '<', today]
        ]);
    }
    openRecentSurveys() {
        this.openAction('nhs.estate.condition', 'list,form');
    }
    openRecentBacklogs() {
        this.openAction('nhs.estate.backlog', 'list,form');
    }
    openRecentAssets() {
        this.openAction('nhs.estate.building', 'list,form');
    }
}

NhsEstateDashboard.template = "odoo_nhs_estate.NhsEstateDashboard";

registry.category("actions").add("nhs_estate_dashboard", NhsEstateDashboard);