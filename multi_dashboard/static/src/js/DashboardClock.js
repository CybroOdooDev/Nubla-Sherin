/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const COLORS = [
    "#ffffff", "#ff9c9c", "#f7c698", "#fde388", "#bbd7f8", "#d9a8cc",
    "#f8d6c8", "#89e1db", "#97a6f9", "#ff9ecc", "#b7edbe", "#e6dbfc"
];

/* DashboardClock component: An analog clock with digital time and date
    display, plus edit/delete options. */
export class DashboardClock extends Component {
    static props = ["*"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            hourAngle: 0,
            minuteAngle: 0,
            digitalTime: "",
            minuteMarks: [],
            hourMarks: [],
            numbers: [],
            date:"",
        });

        this.generateDial();
        this.updateClock();

        let timer;
        onMounted(() => {
            timer = setInterval(() => this.updateClock(), 1000);
        });
        onWillUnmount(() => clearInterval(timer));
    }

    // Pre-calculate positions for minute marks, hour marks, and numbers
    generateDial() {
        const center = 50;
        const radius = 45;

        // Minute dots (60)
        for (let i = 0; i < 60; i++) {
            const angle = (i * 6 - 90) * Math.PI / 180;
            this.state.minuteMarks.push({
                x: center + Math.cos(angle) * radius,
                y: center + Math.sin(angle) * radius,
            });
        }

        // Hour marks (12)
        for (let i = 0; i < 12; i++) {
            const angle = (i * 30 - 90) * Math.PI / 180;
            this.state.hourMarks.push({
                x1: center + Math.cos(angle) * (radius - 6),
                y1: center + Math.sin(angle) * (radius - 6),
                x2: center + Math.cos(angle) * radius,
                y2: center + Math.sin(angle) * radius,
            });
        }

        // Numbers
        for (let i = 1; i <= 12; i++) {
            const angle = (i * 30 - 90) * Math.PI / 180;
            this.state.numbers.push({
                value: i,
                x: center + Math.cos(angle) * (radius - 12),
                y: center + Math.sin(angle) * (radius - 12),
            });
        }
    }
    // Helper to get the hex code based on the prop integer
    get accentColor() {
        const index = this.props.data.todo_color || 0;
        return COLORS[index] || COLORS[0];
    }

    // Update clock angles and digital time/date every second
    updateClock() {
        const recordData = this.props.data;
        // Fallback to UTC if no timezone is provided
        const timezone = recordData.tz || "UTC";
        const is24h = recordData.clock_format === '24';

        // Get the time in the specific timezone
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: timezone,
            hour12: false,
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric',
            year: 'numeric',
            month: 'numeric',
            day: 'numeric'
        });

        const parts = formatter.formatToParts(now);
        const dateMap = {};
        parts.forEach(p => dateMap[p.type] = p.value);

        // Convert strings to integers for calculations
        const hours = parseInt(dateMap.hour);
        const minutes = parseInt(dateMap.minute);
        const seconds = parseInt(dateMap.second);

        // Update Analog Hand Angles
        this.state.minuteAngle = minutes * 6 + seconds * 0.1;
        this.state.hourAngle = (hours % 12) * 30 + minutes * 0.5;

        // Update Digital Time Display based on clock_format
        let timeString = now.toLocaleTimeString([], {
            timeZone: timezone,
            hour12: !is24h,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });

        this.state.digitalTime = is24h ? timeString : timeString.toUpperCase();

        // Update Date Display based on timezone
        this.state.date = now.toLocaleDateString(undefined, {
            timeZone: timezone,
            weekday: 'long',
            month: 'long',
            day: 'numeric'
        });
    }

    // Open the edit form view for this clock record. After closing, trigger a refresh.
    onEdit() {
        const clockId = this.props.data.id; // Assuming you pass the record ID in props
        if (!clockId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts", // Your model name
            res_id: clockId,
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                // Trigger a refresh. Since this is a child,
                // it's best to call a prop passed from MultiDashboard.
                if (this.props.onRefresh) {
                    await this.props.onRefresh();
                }
            }
        });
    }

    // Unlink the record from the dashboard. After deletion, trigger a refresh.
    onDelete() {
        const clockId = this.props.data.id; // Assuming you pass the record ID in props
        if (!clockId) return;

        this.orm.unlink('multi.dashboard.charts', [clockId]).then(() => {
            // it's best to call a prop passed from MultiDashboard.
            if (this.props.onDelete) {
                this.props.onDelete();
            }
        });
    }

    // Trigger the JSON export for this chart. The export logic is handled in the method below.
    downloadJson() {
        this.downloadJsonExport({ chart_id: this.props.data.id });
    }

    // Call the server method to get the JSON export content, then create a downloadable file for the user.
    async downloadJsonExport(exportParams) {
        /**
         * exportParams can be:
         * { dashboard_id: 1 } OR { chart_id: 5 }
         */
        try {
            const result = await this.orm.call(
                "multi.dashboard.charts",
                "export_to_json",
                [],
                exportParams
            );

            if (!result) return;

            const blob = new Blob([result.content], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error("Export failed:", error);
        }
    }
}

DashboardClock.template = xml`
    <div class="clock-widget d-flex flex-column align-items-center justify-content-center h-100 shadow-sm rounded p-2"
         t-attf-style="--widget-accent: {{ this.accentColor }};">

         <div class="clock-tools-overlay">
            <button class="btn-edit-clock" t-on-click="onEdit">
                <i class="fa fa-pencil"/>
            </button>
            <button class="btn-del-clock" t-on-click="onDelete">
                <i class="fa fa-trash"/>
            </button>
        </div>
        <div t-if="!props.isPreview" class="download-options">
            <button class="btn-download-json" t-on-click="downloadJson">
                <i class="fa fa-download"/>
            </button>
        </div>

        <svg width="160" height="160" viewBox="0 0 100 100" class="mb-2">
            <circle cx="50" cy="50" r="46" fill="none" stroke="#ddd" stroke-width="1"/>

            <t t-foreach="state.minuteMarks" t-as="mark" t-key="mark_index">
                <circle t-att-cx="mark.x" t-att-cy="mark.y" r="0.8" fill="#000"/>
            </t>

            <t t-foreach="state.hourMarks" t-as="mark" t-key="mark_index">
                <line t-att-x1="mark.x1" t-att-y1="mark.y1"
                      t-att-x2="mark.x2" t-att-y2="mark.y2"
                      stroke="#000" stroke-width="2"/>
            </t>

            <!-- Numbers -->
            <t t-foreach="state.numbers" t-as="num" t-key="num.value">
                <text t-att-x="num.x" t-att-y="num.y"
                      text-anchor="middle"
                      dominant-baseline="middle"
                      font-size="6"
                      fill="#222">
                    <t t-esc="num.value"/>
                </text>
            </t>

            <!-- Hour Hand -->
            <line x1="50" y1="50" x2="50" y2="28"
                  stroke="#000" stroke-width="3" stroke-linecap="round"
                  t-attf-style="transform: rotate({{state.hourAngle}}deg); transform-origin: 50px 50px; transition: transform 0.5s ease;"/>

            <!-- Minute Hand -->
            <line x1="50" y1="50" x2="50" y2="18"
                  stroke="#555659" stroke-width="2" stroke-linecap="round"
                  t-attf-style="transform: rotate({{state.minuteAngle}}deg); transform-origin: 50px 50px; transition: transform 0.3s ease;"/>

            <!-- Center -->
            <circle cx="50" cy="50" r="1.8" fill="#000"/>
        </svg>

        <div class="fw-bold text-dark" style="font-variant-numeric: tabular-nums;">
            <t t-esc="state.digitalTime"/>
        </div>
        <div class="small text-primary" t-if="props.data.tz">
            <t t-esc="props.data.tz"/>
        </div>
        <div class="text-uppercase tracking-wider text-muted fw-light" t-esc="state.date"/>
        <div t-if="props.data.name" class="small text-muted text-truncate w-100 text-center" t-esc="props.data.name"/>
    </div>
`;
