/** @odoo-module **/
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { DashboardTileWidget } from "./DashboardTileWidget";
import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardListWidget } from "./DashboardListWidget";
import { DashboardTodoWidget } from "./DashboardTodoWidget";
import { DashboardChart } from "./DashboardChart";
import { DashboardClock } from "./DashboardClock";
import { DashboardProgressBar } from "./DashboardProgressBar";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount, onWillUpdateProps, mount } from "@odoo/owl";


/* MultiDashboard Client Action
This component renders a customizable dashboard where users can add, move, and
resize various widgets (charts, tiles, lists, etc.). It uses GridStack.js for the
drag-and-drop layout and supports saving the dashboard state to the backend.
Users with manager access can edit the layout, while others can only view and export.
*/
export class MultiDashboard extends Component {
    static props = ["*"];
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.isLoading = false;

        // Track mounted Owl components by widget record ID for targeted cleanup
        this.mountedComponents = {};

        const params = this.props.action.params || {};
        this.dashboardId = params.dashboard_id || null;

        this.state = useState({
            dashboardId: this.dashboardId,
            dashboardName: this.props.action.name || "Dashboard",
            sidebarVisible: false,
            sidebarWidth: 300,
            currentPage: {},
            loading: true,
            isEmpty: false,
            isManager: false,
            isCompact: false,
            theme: params.theme || 'light',
            refreshInterval: 0,
            nlpQuery: '',
            isGeneratingChart: false,
        });

        this.sidebar = useRef("sidebar");
        this.resizeHandle = useRef("resizeHandle");
        this.gridRef = useRef("grid");
        this.grid = null;

        this.isResizing = false;
        this.startX = 0;
        this.startWidth = 0;

        onWillStart(async () => {
            this.state.isManager = await user.hasGroup("multi_dashboard.group_multi_dashboard_manager");
            const dashboards = await this.orm.searchRead(
                'multi.dashboards',
                [['id', '=', this.state.dashboardId]],
                ['theme', 'refresh_interval']
            );
            if (dashboards.length) {
                this.state.theme = dashboards[0].theme;
                this.state.refreshInterval = parseInt(dashboards[0].refresh_interval) || 0;
            }
        });

        onMounted(async () => {
            const savedWidth = localStorage.getItem('dashboard_sidebar_width');
            if (savedWidth) {
                this.state.sidebarWidth = parseInt(savedWidth);
            }

            document.addEventListener('mousemove', this.onResize.bind(this));
            document.addEventListener('mouseup', this.onResizeEnd.bind(this));

            await this.initGrid();
            await this.loadWidgets();

            // Start the timer if an interval is set in the database
            if (this.state.refreshInterval > 0) {
                this.startRefreshTimer(this.state.refreshInterval);
            }
            this.state.loading = false;
        });

        onWillUnmount(() => {
            document.removeEventListener('mousemove', this.onResize.bind(this));
            document.removeEventListener('mouseup', this.onResizeEnd.bind(this));

            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null; // Clean up the reference
            }

            if (this.grid) this.grid.destroy(false);
        });

        onWillUpdateProps(async (nextProps) => {
            const nextParams = nextProps.action.params || {};
            const nextDashboardId = nextParams.dashboard_id || null;
            if (nextDashboardId && nextDashboardId !== this.state.dashboardId) {
                this.dashboardId = nextDashboardId;
                this.state.dashboardId = nextDashboardId;
                this.state.dashboardName = nextProps.action.name || "Dashboard";
                this.state.loading = true;

                const dashboards = await this.orm.searchRead('multi.dashboards', [['id', '=', this.state.dashboardId]], ['theme']);
                if (dashboards.length) {
                    this.state.theme = dashboards[0].theme;
                }

                await this.loadWidgets();
                this.state.loading = false;
            }
        });
    }

    // Handlers for sidebar resizing
    onResizeStart(ev) {
        ev.preventDefault();
        this.isResizing = true;
        this.startX = ev.clientX;
        this.startWidth = this.state.sidebarWidth;

        document.body.classList.add('resizing-sidebar');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }

    // Mousemove handler to resize the sidebar in real-time, with min/max constraints
    onResize(ev) {
        if (!this.isResizing) return;

        const deltaX = ev.clientX - this.startX;
        let newWidth = this.startWidth + deltaX;

        const minWidth = 200;
        const maxWidth = 400;

        newWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
        this.state.sidebarWidth = newWidth;
    }

    // Mouseup handler to finalize resizing, save width to localStorage, and clean up styles
    onResizeEnd(ev) {
        if (!this.isResizing) return;

        this.isResizing = false;
        localStorage.setItem('dashboard_sidebar_width', this.state.sidebarWidth);

        document.body.classList.remove('resizing-sidebar');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }

    // Export the current dashboard configuration to JSON and trigger a download in the browser
    async exportDashboard() {
        try {
            const result = await this.orm.call(
                "multi.dashboard.charts",
                "export_to_json",
                [],
                { dashboard_id: this.dashboardId }
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

    // Open a form view to import a dashboard from JSON. On close, reload the dashboard
    async importDashboard() {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }

        const existingIds = new Set(Object.keys(this.mountedComponents));

        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Import Dashboard from JSON',
            res_model: 'import.chart',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_dashboard_id': this.dashboardId,
            }
        }, {
            onClose: async () => {
                const allWidgets = await this.orm.call(
                    'multi.dashboard.charts',
                    'get_dashboard_widgets',
                    [this.dashboardId],
                );

                if (!allWidgets || allWidgets.length === 0) {
                    // Import was cancelled or resulted in empty dashboard
                    return;
                }

                // Separate into new widgets vs existing ones that may have moved/resized
                const newWidgets = allWidgets.filter(w => !existingIds.has(String(w.id)));
                const updatedWidgets = allWidgets.filter(w => existingIds.has(String(w.id)));

                for (const w of updatedWidgets) {
                    const gridEl = this.gridRef.el.querySelector(`[data-record-id="${w.id}"]`);
                    if (gridEl) {
                        this.grid.update(gridEl, {
                            x: w.gs_x,
                            y: w.gs_y,
                            w: w.gs_w,
                            h: w.gs_h,
                        });
                    }
                }

                // For brand-new widgets: inject them individually without touching others
                for (const w of newWidgets) {
                    await this._addWidgetToGrid(w);
                }

                this.state.isEmpty = allWidgets.length === 0;
            }
        });
    }

    // Initialize the GridStack layout with options and event handlers for adding, changing, and resizing widgets
    initGrid() {
        this.grid = GridStack.init({
            float: true,
            cellHeight: 100,
            column: 12,
            margin: 5,
            acceptWidgets: true,
            animate: true,
            staticGrid: !this.state.sidebarVisible,
            minRow: 12,
        }, this.gridRef.el);

        GridStack.setupDragIn('.dashboard-tile', {
            appendTo: 'body',
            helper: 'clone',
            revert: 'invalid',
            scroll: false,
        });

        this.grid.on('added', (event, items) => {
            if (this.isLoading) return;
            items.forEach((item) => {
                if (!item.el.dataset.recordId) {
                    this.handleNewWidgetDrop(item);
                }
            });
        });

        this.grid.on('change', (event, items) => {
            this.saveLayout(items);
        });

        this.grid.on('resizestop', (event, el) => {
            this.grid.compact();
            const node = el.gridstackNode;
            if (node) {
                this.saveLayout([node]);
            }
        });
    }

    /**
     * Destroy and remove the Owl component mounted for a specific widget ID.
     * @param {number|string} recordId
     */
    _destroyWidgetComponent(recordId) {
        const id = String(recordId);
        if (this.mountedComponents[id]) {
            try {
                this.mountedComponents[id].destroy();
            } catch (e) {
                // Component may already be gone — safe to ignore
            }
            delete this.mountedComponents[id];
        }
    }

    /**
     * Remove a single widget from the grid by its record ID, without touching
     * any other widget. Called by child components via the onDelete callback.
     * @param {number} recordId
     */
    removeWidget(recordId) {
        const id = String(recordId);

        // Destroy the mounted Owl component first
        this._destroyWidgetComponent(id);

        // Find and remove the grid-stack item element
        const gridEl = this.gridRef.el.querySelector(`[data-record-id="${id}"]`);
        if (gridEl) {
            this.grid.removeWidget(gridEl, true); // true = remove DOM node
        }

        // Update empty-state flag
        const remaining = this.gridRef.el.querySelectorAll('.grid-stack-item[data-record-id]');
        this.state.isEmpty = remaining.length === 0;
    }

    /**
     * Refresh a single widget in place: fetch fresh data from the backend,
     * destroy the old component, clear the content element, and re-mount.
     * Called by child components via the onRefresh callback.
     * @param {number} recordId
     */
    async refreshWidget(recordId) {
        const id = String(recordId);

        // Find the DOM nodes for this widget
        const gridEl = this.gridRef.el.querySelector(`[data-record-id="${id}"]`);
        if (!gridEl) {
            // Widget no longer in DOM — fall back to full reload
            await this.loadWidgets();
            return;
        }

        const gridContent = gridEl.querySelector('.grid-stack-item-content');
        if (!gridContent) return;

        try {
            // Fetch latest widget metadata + fresh data in parallel
            const [widgets, data] = await Promise.all([
                this.orm.call('multi.dashboard.charts', 'get_dashboard_widgets', [this.dashboardId]),
                this.orm.call('multi.dashboard.charts', 'get_widget_value', [parseInt(id)]),
            ]);

            const widget = widgets.find(w => String(w.id) === id);
            if (!widget) {
                // Widget was deleted on the backend — remove it from the grid
                this.removeWidget(id);
                return;
            }

            // Tear down the old Owl component
            this._destroyWidgetComponent(id);

            // Wipe the content container and re-render into it
            gridContent.innerHTML = '';
            await this.renderWidgetContent(widget, data, gridContent, id);
        } catch (e) {
            console.error(`Error refreshing widget ${id}`, e);
        }
    }

    /**
     * Full dashboard reload — used on initial load and after import.
     * Destroys all mounted components and rebuilds the grid from scratch.
     */
    async loadWidgets() {
        // Destroy every tracked Owl component
        for (const id of Object.keys(this.mountedComponents)) {
            this._destroyWidgetComponent(id);
        }
        this.mountedComponents = {};
        this.grid.removeAll();

        try {
            const widgets = await this.orm.call(
                'multi.dashboard.charts',
                'get_dashboard_widgets',
                [this.dashboardId],
            );

            this.state.isEmpty = widgets.length === 0;

            if (!this.state.isEmpty) {
                // Mount all widgets in parallel; _addWidgetToGrid handles DOM + Owl
                await Promise.all(widgets.map(w => this._addWidgetToGrid(w)));
            }
        } catch (e) {
            console.error("Error loading widgets", e);
        } finally {
            if (this.grid) {
                setTimeout(() => {
                    this.grid.setStatic(!this.state.sidebarVisible);
                }, 100);
            }
        }
    }

    /**
     * Mount the correct Owl component for a widget into targetEl.
     * recordId is stored so the component can be tracked and torn down individually.
     *
     * onRefresh  → refreshes only THIS widget (targeted, fast)
     * onDelete   → removes only THIS widget from the grid (no re-render at all)
     *
     * @param {Object} widget
     * @param {Object} data
     * @param {HTMLElement} targetEl
     * @param {number|string} recordId
     */
    async renderWidgetContent(widget, data, targetEl, recordId) {
        const id = String(recordId);

        // Callbacks that target only this one widget
        const onRefresh = async () => await this.refreshWidget(id);
        const onDelete  = () => this.removeWidget(id);

        let comp;

        if (widget.chart_type === 'tile') {
            comp = await mount(DashboardTileWidget, targetEl, {
                props: { widget, data, onRefresh, onDelete },
                env: this.env,
            });
        } else if (widget.chart_type === 'clock') {
            comp = await mount(DashboardClock, targetEl, {
                props: { data, onRefresh, onDelete },
                env: this.env,
            });
        } else if (widget.chart_type === 'list') {
            comp = await mount(DashboardListWidget, targetEl, {
                props: {
                    name: widget.name,
                    model: widget.model_name,
                    data,
                    onRefresh,
                    onDelete,
                },
                env: this.env,
            });
        } else if (widget.chart_type === 'todo') {
            comp = await mount(DashboardTodoWidget, targetEl, {
                props: {
                    name: widget.name,
                    data,
                    recordId: widget.id,
                    color: widget.todo_color || 0,
                    onRefresh,
                    onDelete,
                },
                env: this.env,
            });
        } else if (widget.chart_type === 'progress') {
            comp = await mount(DashboardProgressBar, targetEl, {
                props: { widget, data, onRefresh, onDelete },
                env: this.env,
            });
        } else {
            comp = await mount(DashboardChart, targetEl, {
                props: {
                    id: widget.id,
                    name: widget.name,
                    data: data.data,
                    series: data.series,
                    chartType: widget.chart_type,
                    color: widget.todo_color || 0,
                    orientation: data.orientation || 'vertical',
                    theme: widget.am_chart_theme || 'default',
                    onRefresh,
                    onDelete,
                },
                env: this.env,
            });
        }

        // Register the component so it can be torn down individually later
        this.mountedComponents[id] = comp;
    }

    // Save the layout changes for the given items to the backend. Called on move/resize events.
    async saveLayout(items) {
        if (!items) return;

        const updates = items.map(item => {
            if (item.id) {
                return this.orm.write('multi.dashboard.charts', [parseInt(item.id)], {
                    gs_x: item.x,
                    gs_y: item.y,
                    gs_w: item.w,
                    gs_h: item.h
                });
            }
        });

        await Promise.all(updates);
    }

    // Toggle the visibility of the sidebar. Only managers can do this; others get an error notification.
    toggleSidebar() {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }
        this.state.sidebarVisible = !this.state.sidebarVisible;

        if (this.grid) {
            this.grid.setStatic(!this.state.sidebarVisible);
        }
    }

    /* Handle the drop of a new widget from the sidebar: open a form view
    to create the widget, then add it to the grid on save */
    async handleNewWidgetDrop(item) {
        const x = item.x !== undefined ? item.x : 0;
        const y = item.y !== undefined ? item.y : 0;

        const type = item.el.dataset.type;
        const defaultW = item.w;
        const defaultH = item.h;

        this.grid.removeWidget(item.el, true);

        const existingIds = new Set(Object.keys(this.mountedComponents));

        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'multi.dashboard.charts',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_dashboard_id: this.dashboardId,
                default_chart_type: type,
                default_gs_x: x,
                default_gs_y: y,
                default_gs_w: defaultW,
                default_gs_h: defaultH,
            }
        }, {
            onClose: async () => {
                const allWidgets = await this.orm.call(
                    'multi.dashboard.charts',
                    'get_dashboard_widgets',
                    [this.dashboardId],
                );

                const newWidgets = allWidgets.filter(w => !existingIds.has(String(w.id)));

                if (newWidgets.length === 0) {
                    // User dismissed the form without saving — nothing to do
                    return;
                }

                // Mount each new widget individually without touching existing ones
                for (const w of newWidgets) {
                    await this._addWidgetToGrid(w);
                }

                this.state.isEmpty = false;
            }
        });
    }

    /**
     * Fetch data for a single widget, create its GridStack item, and mount its
     * Owl component — without disturbing any already-rendered widgets.
     * @param {Object} w  Widget record from get_dashboard_widgets
     */
    async _addWidgetToGrid(w) {
        try {
            const data = await this.orm.call('multi.dashboard.charts', 'get_widget_value', [w.id]);

            const gridItem = document.createElement('div');
            gridItem.className = 'grid-stack-item';
            gridItem.setAttribute('gs-x', w.gs_x);
            gridItem.setAttribute('gs-y', w.gs_y);
            gridItem.setAttribute('gs-w', w.gs_w);
            gridItem.setAttribute('gs-h', w.gs_h);
            gridItem.setAttribute('gs-id', w.id);
            gridItem.dataset.recordId = w.id;

            const gridContent = document.createElement('div');
            gridContent.className = 'grid-stack-item-content shadow-sm rounded';
            gridItem.appendChild(gridContent);

            this.isLoading = true;
            this.gridRef.el.appendChild(gridItem);
            this.grid.makeWidget(gridItem);
            this.isLoading = false;

            await this.renderWidgetContent(w, data, gridContent, w.id);
        } catch (e) {
            console.error(`Error adding widget ${w.id} to grid`, e);
            this.isLoading = false;
        }
    }

    // Capture the entire dashboard as a PNG using dom-to-image, then generate a multi-page PDF with jsPDF.
    async printDashboard(for_mail) {
        const { jsPDF } = window.jspdf;
        this.notification.add("Capturing full dashboard layout...", { type: "info" });

        const element = this.gridRef.el;
        const margin = 20;

        try {
            const fullCanvasData = await domtoimage.toPng(element, {
                quality: 1,
                bgcolor: '#f4f7fa',
                style: {
                    'border': 'none',
                    'box-shadow': 'none'
                }
            });

            return await new Promise((resolve, reject) => {
                const img = new Image();
                img.src = fullCanvasData;

                img.onload = () => {
                    const doc = new jsPDF('p', 'px', 'a3');
                    const pageWidth = doc.internal.pageSize.getWidth();
                    const pageHeight = doc.internal.pageSize.getHeight();

                    const contentWidth = pageWidth - (margin * 2);
                    const scale = contentWidth / img.width;
                    const scaledHeight = img.height * scale;

                    let heightLeft = scaledHeight;
                    let position = margin;

                    doc.addImage(fullCanvasData, 'PNG', margin, position, contentWidth, scaledHeight);
                    heightLeft -= (pageHeight - margin);

                    while (heightLeft > 0) {
                        position = heightLeft - scaledHeight + margin;
                        doc.addPage();
                        doc.addImage(fullCanvasData, 'PNG', margin, position, contentWidth, scaledHeight);
                        heightLeft -= pageHeight;
                    }

                    if (for_mail) {
                        const pdfBase64 = doc.output('datauristring').split(',')[1];
                        this.notification.add("PDF generated for email.", { type: "success" });
                        resolve(pdfBase64);
                    } else {
                        doc.save("Dashboard_Full_Report.pdf");
                        this.notification.add("Export Complete", { type: "success" });
                        resolve(null);
                    }
                };
                img.onerror = (e) => reject(e);
            });
        } catch (err) {
            console.error("Full capture failed", err);
            this.notification.add("Export failed. Try a smaller range.", { type: "danger" });
        }
    }

    // Generate the PDF and trigger the email composition action with the PDF attached.
    async sendDashboard() {
        const pdfData = await this.printDashboard(true);
        const exportResult = await this.orm.call(
            "multi.dashboard.charts",
            "export_to_json",
            [],
            { dashboard_id: this.dashboardId }
        );
        if (pdfData && exportResult) {
            const jsonBase64 = btoa(unescape(encodeURIComponent(exportResult.content)));

            const action = await this.orm.call(
                "multi.dashboards",
                "action_prepare_dashboard_mail",
                [],
                {
                    dashboard_id: this.dashboardId,
                    pdf_base64: pdfData,
                    json_base64: jsonBase64,
                    json_filename: exportResult.filename
                }
            );
            if (action) {
                await this.action.doAction(action);
            }
        }
    }

    /* Toggle between compact and spacious grid layouts. Compact mode moves
    widgets up to fill gaps, while spacious mode preserves their positions with more whitespace.*/
    toggleCompactView() {
        this.state.isCompact = !this.state.isCompact;
        if (this.grid) {
            this.grid.compact('compact');

            const items = this.grid.getGridItems().map(el => el.gridstackNode);
            this.saveLayout(items);
        }
    }

    async generateChartFromText() {
        if (!this.state.nlpQuery || !this.state.nlpQuery.trim() || this.state.isGeneratingChart) return;

        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit dashboards.", { type: "danger" });
            return;
        }

        this.state.isGeneratingChart = true;
        try {
            const result = await this.orm.call(
                "multi.dashboards",
                "generate_chart_from_text",
                [this.dashboardId, this.state.nlpQuery.trim()]
            );

            if (result && result.success) {
                const successMsg = result.message || "Chart generated successfully!";
                if (result.errors && result.errors.length > 0) {
                    this.notification.add(`${successMsg} with some errors: ${result.errors.join(', ')}`, { type: "warning" });
                } else {
                    this.notification.add(successMsg, { type: "success" });
                }
                this.state.nlpQuery = '';
                await this.loadWidgets();
            } else {
                this.notification.add(result.error || "Failed to generate chart.", { type: "danger" });
            }
        } catch (error) {
            console.error("Error generating chart:", error);
            this.notification.add("An error occurred while generating the chart.", { type: "danger" });
        } finally {
            this.state.isGeneratingChart = false;
        }
    }

    onNlpInputKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            this.generateChartFromText();
        }
    }

    /**
     * Change the overall dashboard theme.
     * Overrides CSS variables globally on the container based on the selected theme.
     * @param {string} themeName  'light', 'dark', 'blue', 'green', 'purple'
     */
    async setTheme(themeName) {
        try {
            await this.orm.write("multi.dashboards", [this.dashboardId], {
                theme: themeName,
            });
            this.state.theme = themeName;
            this.notification.add("Theme updated", { type: "success" });
        } catch (error) {
            this.notification.add("Could not save theme", { type: "danger" });
        }
    }

    // Helper to manage the actual JS interval
    startRefreshTimer(minutes) {
        if (this.refreshTimer) clearInterval(this.refreshTimer);
        this.refreshTimer = setInterval(() => {
            this.refreshAllWidgets();
        }, minutes * 60 * 1000);
    }

    async setRefreshInterval(minutes) {
        try {
            // 1. Persist to Database
            await this.orm.write("multi.dashboards", [this.dashboardId], {
                refresh_interval: String(minutes),
            });

            // 2. Update Local State
            this.state.refreshInterval = minutes;

            // 3. Update Timer
            if (minutes > 0) {
                this.startRefreshTimer(minutes);
                this.notification.add(`Auto-refresh saved: ${minutes}m`, { type: "info" });
            } else {
                if (this.refreshTimer) clearInterval(this.refreshTimer);
                this.notification.add("Auto-refresh disabled", { type: "info" });
            }
        } catch (error) {
            this.notification.add("Could not save refresh interval", { type: "danger" });
        }
    }

    async refreshAllWidgets() {
        for (const recordId of Object.keys(this.mountedComponents)) {
            await this.refreshWidget(recordId);
        }
    }
}

MultiDashboard.components = { DashboardSidebar };
MultiDashboard.template = "owl.MultiDashboard"
registry.category("actions").add("MultiDashboardClientAction", MultiDashboard)
