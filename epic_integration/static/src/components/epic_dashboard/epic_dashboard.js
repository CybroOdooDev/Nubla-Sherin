/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

class EpicDashboard extends Component {
    static template = "epic_integration.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true, error: null });

        this.patientChartRef = useRef("patientChart");
        this.appointmentChartRef = useRef("appointmentChart");
        this.conditionChartRef = useRef("conditionChart");
        this.allergyStatusChartRef = useRef("allergyStatusChart");
        this.allergyCategoryChartRef = useRef("allergyCategoryChart");

        this._charts = [];

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        onMounted(async () => {
            await this._loadData();
        });

        onWillUnmount(() => {
            this._destroyCharts();
        });
    }

    async _loadData() {
        try {
            const data = await this.orm.call("epic.dashboard", "get_dashboard_data", []);
            this.state.data = data;
            this.state.loading = false;
            // Give OWL one tick to render the canvas elements before drawing
            setTimeout(() => this._renderCharts(), 100);
        } catch (e) {
            this.state.loading = false;
            this.state.error = "Failed to load dashboard data. Please try refreshing.";
        }
    }

    _destroyCharts() {
        this._charts.forEach((c) => { try { c.destroy(); } catch (_) {} });
        this._charts = [];
    }

    _renderCharts() {
        if (!this.state.data) return;
        this._destroyCharts();

        const d = this.state.data;

        // NHS colour palette
        const BLUE   = "#005EB8";
        const AQUA   = "#41B6E6";
        const GREEN  = "#007F3B";
        const RED    = "#D5281B";
        const YELLOW = "#FFB81C";
        const DARK   = "#003087";
        const PINK   = "#E87D7D";

        this._pie(this.patientChartRef.el, {
            labels: ["Male", "Female", "Other / Unknown"],
            data: [d.patients.male, d.patients.female, d.patients.other],
            colors: [BLUE, PINK, AQUA],
        });

        this._bar(this.appointmentChartRef.el, {
            labels: ["Booked", "Arrived", "Fulfilled", "Cancelled", "Proposed/Pending"],
            data: [
                d.appointments.booked,
                d.appointments.arrived,
                d.appointments.fulfilled,
                d.appointments.cancelled,
                d.appointments.proposed,
            ],
            colors: [BLUE, GREEN, AQUA, RED, YELLOW],
        });

        this._doughnut(this.conditionChartRef.el, {
            labels: ["Active", "Inactive", "Resolved"],
            data: [d.conditions.active, d.conditions.inactive, d.conditions.resolved],
            colors: [DARK, AQUA, GREEN],
        });

        this._doughnut(this.allergyStatusChartRef.el, {
            labels: ["Active", "Inactive", "Resolved"],
            data: [d.allergies.active, d.allergies.inactive, d.allergies.resolved],
            colors: [RED, YELLOW, GREEN],
        });

        this._bar(this.allergyCategoryChartRef.el, {
            labels: ["Food", "Medication", "Environment", "Biologic"],
            data: [
                d.allergies.food,
                d.allergies.medication,
                d.allergies.environment,
                d.allergies.biologic,
            ],
            colors: [YELLOW, RED, GREEN, AQUA],
        });
    }

    _pie(canvas, { labels, data, colors }) {
        if (!canvas) return;
        const c = new Chart(canvas, {
            type: "pie",
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: "#fff" }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { padding: 10, font: { size: 11 } } },
                },
            },
        });
        this._charts.push(c);
    }

    _doughnut(canvas, { labels, data, colors }) {
        if (!canvas) return;
        const c = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: "#fff" }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "60%",
                plugins: {
                    legend: { position: "bottom", labels: { padding: 10, font: { size: 11 } } },
                },
            },
        });
        this._charts.push(c);
    }

    _bar(canvas, { labels, data, colors }) {
        if (!canvas) return;
        const bgColors = Array.isArray(colors) ? colors.map((c) => c + "BB") : [colors + "BB"];
        const borderColors = Array.isArray(colors) ? colors : [colors];
        const c = new Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        data,
                        backgroundColor: bgColors,
                        borderColor: borderColors,
                        borderWidth: 2,
                        borderRadius: 5,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, precision: 0 },
                        grid: { color: "#f0f0f0" },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
        this._charts.push(c);
    }

    navigateTo(xmlid) {
        this.action.doAction(xmlid);
    }
}

registry.category("actions").add("epic_integration.dashboard", EpicDashboard);
