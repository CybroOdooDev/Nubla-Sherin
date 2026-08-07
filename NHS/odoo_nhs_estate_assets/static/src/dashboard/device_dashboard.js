/** @odoo-module **/

import { Component, onWillStart, useState, useEffect, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

export class NhsDeviceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            metrics: null,
            loading: true,
        });

        // Chart References
        this.categoryChartRef = useRef("categoryChart");
        this.statusChartRef = useRef("statusChart");
        this.dueVsOverdueChartRef = useRef("dueVsOverdueChart");
        this.plannerChartRef = useRef("plannerChart");
        this.alertSourceChartRef = useRef("alertSourceChart");
        this.replacementChartRef = useRef("replacementChart");
        this.valueCategoryChartRef = useRef("valueCategoryChart");

        this.chartInstances = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadMetrics();
        });

        useEffect(() => {
            if (!this.state.loading && this.state.metrics) {
                this.renderCharts();
            }
        }, () => [this.state.loading]);

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadMetrics() {
        this.state.loading = true;
        try {
            this.state.metrics = await this.orm.call("nhs.device", "get_dashboard_metrics", []);
        } catch (error) {
            console.error("Error loading NHS Device Dashboard metrics:", error);
        } finally {
            this.state.loading = false;
        }
    }

    destroyCharts() {
        Object.values(this.chartInstances).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.chartInstances = {};
    }

    renderCharts() {
        this.destroyCharts();
        const metrics = this.state.metrics;
        if (!metrics) return;

        const labelFont = { family: 'Outfit, Inter, sans-serif', size: 12, weight: '500' };
        const titleFont = { family: 'Outfit, Inter, sans-serif', size: 13, weight: '600' };

        // 1. Devices by Category (Doughnut Chart)
        if (this.categoryChartRef.el && metrics.devices_by_category) {
            const topCategories = metrics.devices_by_category.slice(0, 6);
            const labels = topCategories.map(c => c.name);
            const dataCounts = topCategories.map(c => c.count);
            const totalCat = dataCounts.reduce((a, b) => a + b, 0);

            this.chartInstances.category = new window.Chart(this.categoryChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataCounts,
                        backgroundColor: ['#003087', '#005EB8', '#41B6E6', '#00A3E0', '#009639', '#768692'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const idx = elements[0].index;
                            const cat = topCategories[idx];
                            if (cat && cat.id) {
                                this.openAction('nhs.device', 'list,form', [['category_id', '=', cat.id]], `Devices - ${cat.name}`);
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { boxWidth: 14, padding: 12, font: titleFont }
                        },
                        tooltip: {
                            bodyFont: labelFont,
                            callbacks: {
                                label: (context) => {
                                    const val = context.parsed || 0;
                                    const pct = totalCat > 0 ? ((val / totalCat) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${val} (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }

        // 2. Devices by Status (Pie / Doughnut Chart)
        if (this.statusChartRef.el && metrics.devices_by_status) {
            const statusData = metrics.devices_by_status;
            const labels = ['In Service', 'Awaiting Repair', 'Out of Service', 'Decommissioned', 'Disposed'];
            const keys = ['in_service', 'awaiting_repair', 'out_of_service', 'decommissioned', 'disposed'];
            const dataCounts = keys.map(k => statusData[k] || 0);
            const totalStatus = dataCounts.reduce((a, b) => a + b, 0);

            this.chartInstances.status = new window.Chart(this.statusChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataCounts,
                        backgroundColor: ['#009639', '#CE7B11', '#DA291C', '#003087', '#768692'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const idx = elements[0].index;
                            const statusKey = keys[idx];
                            this.openAction('nhs.device', 'list,form', [['status', '=', statusKey]], `Devices - ${labels[idx]}`);
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { boxWidth: 14, padding: 12, font: titleFont }
                        },
                        tooltip: {
                            bodyFont: labelFont,
                            callbacks: {
                                label: (context) => {
                                    const val = context.parsed || 0;
                                    const pct = totalStatus > 0 ? ((val / totalStatus) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${val} (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }

        // 3. Maintenance Due vs Overdue Chart (Grouped Bar Chart)
        if (this.dueVsOverdueChartRef.el && metrics.maintenance_planner && metrics.overdue_register) {
            const duePpm = metrics.maintenance_planner.due_soon_ppm || 0;
            const dueCalib = metrics.maintenance_planner.due_soon_calib || 0;
            const overduePpm = metrics.overdue_register.overdue_ppm_count || 0;
            const overdueCalib = metrics.overdue_register.overdue_calib_count || 0;

            this.chartInstances.dueVsOverdue = new window.Chart(this.dueVsOverdueChartRef.el, {
                type: 'bar',
                data: {
                    labels: ['PPM Maintenance', 'Calibration & Safety'],
                    datasets: [
                        {
                            label: 'Due Soon',
                            data: [duePpm, dueCalib],
                            backgroundColor: '#CE7B11',
                            borderRadius: 4,
                            maxBarThickness: 35
                        },
                        {
                            label: 'Overdue',
                            data: [overduePpm, overdueCalib],
                            backgroundColor: '#DA291C',
                            borderRadius: 4,
                            maxBarThickness: 35
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const datasetIndex = elements[0].datasetIndex;
                            if (datasetIndex === 0) {
                                this.openDueSoonSchedules();
                            } else {
                                this.openOverdueSchedules();
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { boxWidth: 12, font: titleFont }
                        },
                        tooltip: { bodyFont: labelFont }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: labelFont } },
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFont, stepSize: 1 }
                        }
                    }
                }
            });
        }

        // 4. Maintenance & Calibration Planner Timeline (Stacked Bar Chart)
        if (this.plannerChartRef.el && metrics.maintenance_planner && metrics.maintenance_planner.timeline) {
            const timeline = metrics.maintenance_planner.timeline;
            const labels = timeline.map(t => t.month);
            const ppmData = timeline.map(t => t.ppm);
            const calibData = timeline.map(t => t.calibration);
            const otherData = timeline.map(t => t.other);

            this.chartInstances.planner = new window.Chart(this.plannerChartRef.el, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'PPM (Maintenance)',
                            data: ppmData,
                            backgroundColor: '#005EB8',
                            borderRadius: 4,
                            maxBarThickness: 35
                        },
                        {
                            label: 'Calibration & Safety',
                            data: calibData,
                            backgroundColor: '#00A3E0',
                            borderRadius: 4,
                            maxBarThickness: 35
                        },
                        {
                            label: 'Other Inspections',
                            data: otherData,
                            backgroundColor: '#768692',
                            borderRadius: 4,
                            maxBarThickness: 35
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { boxWidth: 12, font: titleFont }
                        },
                        tooltip: { bodyFont: labelFont }
                    },
                    scales: {
                        x: { stacked: true, grid: { display: false }, ticks: { font: labelFont } },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFont, stepSize: 1 }
                        }
                    }
                }
            });
        }

        // 5. Safety Alert Exposure by Source (Bar Chart)
        if (this.alertSourceChartRef.el && metrics.safety_alerts) {
            const src = metrics.safety_alerts.source_exposure;
            const labels = ['MHRA', 'CAS', 'Manufacturer FSN', 'Other'];
            const dataCounts = [src.mhra || 0, src.cas || 0, src.manufacturer_fsn || 0, src.other || 0];

            this.chartInstances.alertSource = new window.Chart(this.alertSourceChartRef.el, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Open Safety Alerts',
                        data: dataCounts,
                        backgroundColor: ['#DA291C', '#CE7B11', '#005EB8', '#768692'],
                        borderRadius: 6,
                        maxBarThickness: 40
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const idx = elements[0].index;
                            const sourceKeys = ['mhra', 'cas', 'manufacturer_fsn', 'other'];
                            this.openAction('nhs.device.alert', 'list,form', [
                                ['source', '=', sourceKeys[idx]],
                                ['state', 'in', ['open', 'in_progress']]
                            ], `Safety Alerts - ${labels[idx]}`);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: { bodyFont: labelFont }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: labelFont } },
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFont, stepSize: 1 }
                        }
                    }
                }
            });
        }

        // 6. Replacement Forecast (Combo Bar + Line Chart)
        if (this.replacementChartRef.el && metrics.replacement_forecast && metrics.replacement_forecast.by_year) {
            const forecast = metrics.replacement_forecast.by_year;
            const labels = forecast.map(f => f.year);
            const counts = forecast.map(f => f.count);
            const costs = forecast.map(f => f.indicative_cost);

            this.chartInstances.replacement = new window.Chart(this.replacementChartRef.el, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            type: 'bar',
                            label: 'Devices Due',
                            data: counts,
                            backgroundColor: '#005EB8',
                            borderRadius: 6,
                            yAxisID: 'yCount',
                            maxBarThickness: 40
                        },
                        {
                            type: 'line',
                            label: 'Est. Replacement Cost (£)',
                            data: costs,
                            borderColor: '#DA291C',
                            backgroundColor: 'rgba(218, 41, 28, 0.1)',
                            borderWidth: 2.5,
                            pointRadius: 4,
                            pointBackgroundColor: '#DA291C',
                            yAxisID: 'yCost',
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, elements) => {
                        if (elements && elements.length > 0) {
                            const idx = elements[0].index;
                            const year = labels[idx];
                            this.openAction('nhs.device', 'list,form', [['replacement_year', '=', parseInt(year)]], `Replacement Forecast - ${year}`);
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: titleFont } },
                        tooltip: {
                            bodyFont: labelFont,
                            callbacks: {
                                label: (context) => {
                                    if (context.dataset.yAxisID === 'yCost') {
                                        return ` Est. Cost: £${context.parsed.y.toLocaleString()}`;
                                    }
                                    return ` Devices: ${context.parsed.y}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: labelFont } },
                        yCount: {
                            type: 'linear',
                            position: 'left',
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: { font: labelFont, stepSize: 1 },
                            title: { display: true, text: 'Device Count', font: labelFont }
                        },
                        yCost: {
                            type: 'linear',
                            position: 'right',
                            beginAtZero: true,
                            grid: { display: false },
                            ticks: {
                                font: labelFont,
                                callback: (val) => {
                                    if (val >= 1000000) return '£' + (val / 1000000).toFixed(1) + 'M';
                                    if (val >= 1000) return '£' + (val / 1000).toFixed(0) + 'k';
                                    return '£' + val;
                                }
                            },
                            title: { display: true, text: 'Cost (£)', font: labelFont }
                        }
                    }
                }
            });
        }

        // 7. Indicative Register Value by Category (Horizontal Bar Chart)
        if (this.valueCategoryChartRef.el && metrics.register_value && metrics.register_value.by_category) {
            const sortedCats = [...metrics.register_value.by_category]
                .sort((a, b) => b.indicative_value - a.indicative_value)
                .slice(0, 7);

            const labels = sortedCats.map(c => c.name);
            const values = sortedCats.map(c => c.indicative_value);

            this.chartInstances.valueCategory = new window.Chart(this.valueCategoryChartRef.el, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Indicative Value (£)',
                        data: values,
                        backgroundColor: '#003087',
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
                            const idx = elements[0].index;
                            const cat = sortedCats[idx];
                            if (cat && cat.id) {
                                this.openAction('nhs.device', 'list,form', [['category_id', '=', cat.id]], `Indicative Value - ${cat.name}`);
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            bodyFont: labelFont,
                            callbacks: {
                                label: (context) => ` Indicative Value: £${context.parsed.x.toLocaleString()}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: '#E8EDEE' },
                            ticks: {
                                font: labelFont,
                                callback: (val) => {
                                    if (val >= 1000000) return '£' + (val / 1000000).toFixed(1) + 'M';
                                    if (val >= 1000) return '£' + (val / 1000).toFixed(0) + 'k';
                                    return '£' + val;
                                }
                            }
                        },
                        y: { grid: { display: false }, ticks: { font: labelFont } }
                    }
                }
            });
        }
    }

    openAction(resModel, viewMode = 'list,form', domain = [], name = 'Details') {
        const views = viewMode.split(',').map(mode => [false, mode]);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
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

    // Quick Action Handlers
    openTotalDevices() {
        this.openAction('nhs.device', 'list,form', [['active', '=', true]], 'All Registered Devices');
    }

    openDueSoonSchedules() {
        this.openAction('nhs.device.schedule', 'list,form', [['status', '=', 'due_soon']], 'Schedules Due Soon');
    }

    openOverdueSchedules() {
        this.openAction('nhs.device.schedule', 'list,form', [['status', '=', 'overdue']], 'Overdue Schedules');
    }

    openSafetyAlerts() {
        this.openAction('nhs.device.alert', 'list,form', [['state', 'in', ['open', 'in_progress']]], 'Open Safety Alerts');
    }

    openAffectedDevices() {
        this.openAction('nhs.device.alert.line', 'list,form', [['action_status', 'in', ['pending', 'quarantined']]], 'Affected Devices');
    }

    openEndOfLifeDevices() {
        const currentYear = new Date().getFullYear();
        this.openAction('nhs.device', 'list,form', [
            '|',
            ['is_end_of_life', '=', true],
            '&', ['replacement_year', '!=', false], ['replacement_year', '<=', currentYear]
        ], 'End-of-Life Devices');
    }

    openIndicativeRegisterValue() {
        this.openAction('nhs.device', 'list,pivot,graph,form', [['active', '=', true]], 'Indicative Register Valuation');
    }

    openReplacementForecast() {
        this.action.doAction('odoo_nhs_estate_assets.action_nhs_device_replacement_forecast');
    }

    createNewDevice() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'New Device',
            res_model: 'nhs.device',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    logService() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Log Service',
            res_model: 'nhs.device.service.wizard',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    formatCurrency(value) {
        if (!value && value !== 0) return '£0';
        return '£' + Math.round(value).toLocaleString();
    }
}

NhsDeviceDashboard.template = "odoo_nhs_estate_assets.NhsDeviceDashboard";

registry.category("actions").add("nhs_device_dashboard", NhsDeviceDashboard);
