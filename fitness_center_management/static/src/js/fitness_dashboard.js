/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getDarkMode, onDarkModeChange, setDarkMode } from "./dark_mode_manager";

class FitnessDashboard extends Component {
    static template = "fitness_center_management.FitnessDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const savedDark = getDarkMode();

        this.state = useState({
            darkMode: savedDark,
            total_members: 0,
            active_subscriptions: 0,
            total_revenue: 0,
            total_trainers: 0,
            total_classes: 0,
            pending_bookings: 0,
            active_equipment: 0,
            maintenance_due: 0,
            recent_members: [],
            subscription_stats: [],
            plan_distribution: [],
            recent_payments: [],
        });

        const off = onDarkModeChange((enabled) => {
            this.state.darkMode = enabled;
        });
        onWillUnmount(() => off());

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const data = await this.orm.call(
            "fitness.member",
            "get_dashboard_data",
            []
        );
        Object.assign(this.state, data);
    }

    toggleDarkMode() {
        setDarkMode(!this.state.darkMode);
    }

    viewMembers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Members",
            res_model: "fitness.member",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewSubscriptions() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Subscriptions",
            res_model: "fitness.subscription",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewTrainers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Trainers",
            res_model: "fitness.trainer",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewClasses() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Classes",
            res_model: "fitness.class",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewBookings() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bookings",
            res_model: "fitness.class.booking",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewEquipment() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Equipment",
            res_model: "fitness.equipment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewPayments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payments",
            res_model: "fitness.payment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewMaintenance() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Maintenance",
            res_model: "fitness.equipment.maintenance",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("fitness_dashboard_action", FitnessDashboard);
