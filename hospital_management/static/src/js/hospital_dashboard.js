/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";

// Main Dashboard Component
class HospitalDashboard extends Component {
    static template = "hospital_management.HospitalDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            dashboardData: {
                total_patients: 0,
                new_patients_today: 0,
                new_patients_week: 0,
                new_patients_month: 0,
                total_appointments_today: 0,
                appointments_confirmed: 0,
                appointments_waiting: 0,
                appointments_completed: 0,
                total_doctors: 0,
                doctors_available: 0,
                doctors_on_leave: 0,
                total_beds: 0,
                beds_occupied: 0,
                beds_available: 0,
                occupancy_percentage: 0,
                pending_lab_tests: 0,
                completed_lab_tests_today: 0,
                pending_surgeries: 0,
                completed_surgeries_today: 0,
                revenue_today: 0,
                revenue_week: 0,
                revenue_month: 0,
            },
            todayAppointments: [],
            recentAdmissions: [],
            criticalLabResults: [],
            upcomingSurgeries: [],
            lowStockMedicines: [],
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            // Refresh dashboard every 5 minutes
            this.refreshInterval = setInterval(() => {
                this.loadDashboardData();
            }, 300000); // 5 minutes
        });
    }

    willUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }

    async loadDashboardData() {
        try {
            this.state.isLoading = true;

            // Load all dashboard statistics
            const data = await this.orm.call(
                "hospital.patient",
                "get_dashboard_data",
                []
            );

            this.state.dashboardData = data.statistics;
            this.state.todayAppointments = data.today_appointments || [];
            this.state.recentAdmissions = data.recent_admissions || [];
            this.state.criticalLabResults = data.critical_lab_results || [];
            this.state.upcomingSurgeries = data.upcoming_surgeries || [];
            this.state.lowStockMedicines = data.low_stock_medicines || [];

        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async refreshDashboard() {
        await this.loadDashboardData();
    }

    // Navigation methods
    async openPatients() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Patients"),
            res_model: "hospital.patient",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    async openTodayAppointments() {
        const today = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Today's Appointments"),
            res_model: "hospital.appointment",
            views: [[false, "list"], [false, "form"], [false, "calendar"]],
            domain: [["appointment_date", "=", today]],
            context: { search_default_today: 1 },
        });
    }

    async openDoctors() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Doctors"),
            res_model: "hospital.doctor",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    async openBeds() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Beds"),
            res_model: "hospital.bed",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    async openLabTests() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Pending Lab Tests"),
            res_model: "hospital.lab.request",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["requested", "sample_collected", "in_progress"]]],
        });
    }

    async openSurgeries() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Upcoming Surgeries"),
            res_model: "hospital.surgery",
            views: [[false, "list"], [false, "form"], [false, "calendar"]],
            domain: [["state", "in", ["scheduled", "pre_op"]]],
        });
    }

    async openLowStockMedicines() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Low Stock Medicines"),
            res_model: "hospital.medicine",
            views: [[false, "list"], [false, "form"]],
            domain: [["is_below_min_stock", "=", true]],
        });
    }

    async openAppointment(appointmentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Appointment"),
            res_model: "hospital.appointment",
            res_id: appointmentId,
            views: [[false, "form"]],
        });
    }

    async openAdmission(admissionId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Admission"),
            res_model: "hospital.admission",
            res_id: admissionId,
            views: [[false, "form"]],
        });
    }

    async openLabRequest(labId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Lab Request"),
            res_model: "hospital.lab.request",
            res_id: labId,
            views: [[false, "form"]],
        });
    }

    async openSurgery(surgeryId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Surgery"),
            res_model: "hospital.surgery",
            res_id: surgeryId,
            views: [[false, "form"]],
        });
    }

    // Utility methods
    formatTime(time) {
        const hours = Math.floor(time);
        const minutes = Math.round((time - hours) * 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    getStateColor(state) {
        const colors = {
            'draft': 'info',
            'confirmed': 'success',
            'waiting': 'warning',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
            'admitted': 'warning',
            'discharged': 'secondary',
        };
        return colors[state] || 'secondary';
    }

    getStateBadge(state) {
        return `badge bg-${this.getStateColor(state)}`;
    }
}

// Register the dashboard action
registry.category("actions").add("hospital.dashboard", HospitalDashboard);

export default HospitalDashboard;