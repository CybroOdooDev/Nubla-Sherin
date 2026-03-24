/** @odoo-module **/
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDate, formatDate, serializeDate } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { DashboardTileWidget } from "./DashboardTileWidget";
import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardChat } from "./DashboardChat";
import { DashboardListWidget } from "./DashboardListWidget";
import { DashboardTodoWidget } from "./DashboardTodoWidget";
import { DashboardChart } from "./DashboardChart";
import { DashboardClock } from "./DashboardClock";
import { DashboardProgressBar } from "./DashboardProgressBar";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount, onWillUpdateProps, mount, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


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
        const odooColorScheme = cookie.get("color_scheme") || "light";

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
            dashboardLayout: 'layout_1',
            odooColorScheme,
            isOdooDark: odooColorScheme === "dark",
            refreshInterval: 0,
            nlpQuery: '',
            isGeneratingChart: false,
            aiSummary: false,
            isSummarizing: false,
            dateFilter: {
                label: 'All Time',
                start_date: null,
                end_date: null
            },
            customStartDate: null,
            customEndDate: null,
            isEditMode: false,
        });

        this.sidebar = useRef("sidebar");
        this.resizeHandle = useRef("resizeHandle");
        this.gridRef = useRef("grid");
        this.dateFilterDropdownButton = useRef("dateFilterDropdownButton");
        this.grid = null;
        this._responsiveObserver = null;
        this._isResponsiveRelayout = false;
        this.boundOnResize = this.onResize.bind(this);
        this.boundOnResizeEnd = this.onResizeEnd.bind(this);
        this.boundHandleDocumentPointerDown = this.handleDocumentPointerDown.bind(this);

        this.isResizing = false;
        this.startX = 0;
        this.startWidth = 0;

        onWillStart(async () => {
            this.state.isManager = await user.hasGroup("multi_dashboard.group_multi_dashboard_manager");
            const dashboards = await this.orm.searchRead(
                'multi.dashboards',
                [['id', '=', this.state.dashboardId]],
                ['theme', 'refresh_interval', 'dashboard_layout']
            );
            if (dashboards.length) {
                this.state.theme = dashboards[0].theme;
                this.state.refreshInterval = parseInt(dashboards[0].refresh_interval) || 0;
                this.state.dashboardLayout = dashboards[0].dashboard_layout || 'layout_1';
            }

            // Load saved date filter
            const savedFilter = localStorage.getItem(`dashboard_filter_${this.state.dashboardId}`);
            if (savedFilter) {
                try {
                    this.state.dateFilter = JSON.parse(savedFilter);
                } catch (e) {
                    console.error("Error parsing saved date filter", e);
                }
            }
        });

        onMounted(async () => {
            const savedWidth = localStorage.getItem('dashboard_sidebar_width');
            if (savedWidth) {
                this.state.sidebarWidth = parseInt(savedWidth);
            }

            document.addEventListener('mousemove', this.boundOnResize);
            document.addEventListener('mouseup', this.boundOnResizeEnd);
            document.addEventListener('pointerdown', this.boundHandleDocumentPointerDown, true);

            await this.initGrid();
            this._setupResponsiveGridColumns();
            await this.loadWidgets();

            // Start the timer if an interval is set in the database
            if (this.state.refreshInterval > 0) {
                this.startRefreshTimer(this.state.refreshInterval);
            }
            this.state.loading = false;
        });

        onWillUnmount(() => {
            document.removeEventListener('mousemove', this.boundOnResize);
            document.removeEventListener('mouseup', this.boundOnResizeEnd);
            document.removeEventListener('pointerdown', this.boundHandleDocumentPointerDown, true);

            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null;
            }

            if (this.loadWidgetsTimer) {
                clearTimeout(this.loadWidgetsTimer);
                this.loadWidgetsTimer = null;
            }

            if (this._responsiveObserver) {
                try {
                    this._responsiveObserver.disconnect();
                } catch (e) {
                    // Ignore observer cleanup errors
                }
                this._responsiveObserver = null;
            }

            if (this._applyResponsive) {
                window.removeEventListener('resize', this._applyResponsive);
            }

            if (this.grid) {
                this.grid.destroy(false);
                this.grid = null;
            }
        });

        onWillUpdateProps(async (nextProps) => {
            const nextParams = nextProps.action.params || {};
            const nextDashboardId = nextParams.dashboard_id || null;
            if (nextDashboardId && nextDashboardId !== this.state.dashboardId) {
                this.dashboardId = nextDashboardId;
                this.state.dashboardId = nextDashboardId;
                this.state.dashboardName = nextProps.action.name || "Dashboard";
                this.state.loading = true;

                const dashboards = await this.orm.searchRead('multi.dashboards', [['id', '=', this.state.dashboardId]], ['theme', 'dashboard_layout']);
                if (dashboards.length) {
                    this.state.theme = dashboards[0].theme;
                    this.state.dashboardLayout = dashboards[0].dashboard_layout || 'layout_1';
                }

                // Load saved date filter for the new dashboard
                const savedFilter = localStorage.getItem(`dashboard_filter_${this.state.dashboardId}`);
                if (savedFilter) {
                    try {
                        this.state.dateFilter = JSON.parse(savedFilter);
                    } catch (e) {
                        console.error("Error parsing saved date filter", e);
                    }
                } else {
                    // Reset to default if no saved filter
                    this.state.dateFilter = {
                        label: 'All Time',
                        start_date: null,
                        end_date: null
                    };
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
            // Responsive columns: desktop 12, tablet 6, mobile 1.
            // Uses GridStack's built-in dynamic columns & per-column layouts.
            columnOpts: {
                columnMax: 12,
                layout: "moveScale",
                breakpoints: [
                    { w: 992, c: 6 },
                    { w: 576, c: 1 },
                ],
            },
            margin: 5,
            acceptWidgets: true,
            animate: true,
            staticGrid: !this.state.isEditMode,
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
            if (this._isResponsiveRelayout) return;
            this.saveLayout(items);
        });

        this.grid.on('resizestop', (event, el) => {
            if (this._isResponsiveRelayout) return;
            this.grid.compact();
            const node = el.gridstackNode;
            if (node) {
                this.saveLayout([node]);
            }
        });
    }

    _setupResponsiveGridColumns() {
        if (!this.gridRef?.el || !this.grid || typeof ResizeObserver === "undefined") return;
        if (this._responsiveObserver) return;

        this._applyResponsive = () => {
            if (!this.grid) return;

            this._isResponsiveRelayout = true;
            try {
                if (typeof this.grid.checkDynamicColumn === "function") {
                    this.grid.checkDynamicColumn();
                }

                // Extra safety: GridStack sometimes gets stuck in 1 column when scaling up
                const width = this.gridRef.el.offsetWidth;
                if (width > 992 && this.grid.getColumn() !== 12) {
                    this.grid.column(12, 'moveScale');
                }
            } finally {
                // change events can fire on the next tick; keep the guard briefly.
                setTimeout(() => {
                    this._isResponsiveRelayout = false;
                }, 0);
            }
        };

        this._responsiveObserver = new ResizeObserver(this._applyResponsive);
        this._responsiveObserver.observe(this.gridRef.el);

        window.addEventListener('resize', this._applyResponsive);

        this._applyResponsive();
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
                this.orm.call('multi.dashboard.charts', 'get_widget_value', [[parseInt(id)]], { date_filter: this.state.dateFilter }),
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
                this.loadWidgetsTimer = setTimeout(() => {
                    if (this.grid && typeof this.grid.setStatic === 'function') {
                        this.grid.setStatic(!this.state.isEditMode);
                    }
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
        const onDelete = () => this.removeWidget(id);

        let comp;

        if (widget.chart_type === 'tile') {
            comp = await mount(DashboardTileWidget, targetEl, {
                props: { widget, data, dateFilter: this.state.dateFilter, onRefresh, onDelete },
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
                    color: widget.todo_color || 0,
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
        } else if (widget.chart_type === 'chat') {
            comp = await mount(DashboardChat, targetEl, {
                props: {
                    id: widget.id,
                    name: widget.name,
                    data: data,
                    onRefresh,
                    onDelete,
                    isManager: this.state.isManager,
                },
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
                    isManager: this.state.isManager,
                    sidebarVisible: this.state.sidebarVisible,
                    modelName: widget.model_name,
                    groupField: data.groupField,
                    groupFieldType: data.groupFieldType,
                    dateGranularity: data.date_granularity,
                    filter: this.state.dateFilter,
                    useBackgroundGradient: widget.use_background_gradient,
                },
                env: this.env,
            });
        }

        // Register the component so it can be torn down individually later
        this.mountedComponents[id] = comp;
    }

    // Save the layout changes for the given items to the backend. Called on move/resize events.
    async saveLayout(items) {
        // Only persist layout when a manager is actively editing (sidebar open).
        // Responsive relayout (dynamic columns) must never be written back to DB.
        if (!this.state.isManager || !this.state.sidebarVisible) return;
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
        this.state.isEditMode = this.state.sidebarVisible;

        if (this.grid && typeof this.grid.setStatic === 'function') {
            this.grid.setStatic(!this.state.isEditMode);
            // Sidebar toggling changes available width; re-evaluate responsive columns.
            if (typeof this.grid.checkDynamicColumn === "function") {
                this._isResponsiveRelayout = true;
                try {
                    this.grid.checkDynamicColumn();
                } finally {
                    setTimeout(() => {
                        this._isResponsiveRelayout = false;
                    }, 0);
                }
            }
        }
    }

    /**
     * Explicitly toggle move/edit mode for layout adjustments.
     */
    toggleEditMode() {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }
        this.state.isEditMode = !this.state.isEditMode;
        if (this.grid && typeof this.grid.setStatic === 'function') {
            this.grid.setStatic(!this.state.isEditMode);
        }
        this.notification.add(this.state.isEditMode ? "Layout Movement Enabled" : "Layout Movement Disabled", { type: "info" });
    }

    /**
     * Change the dashboard layout and rearrange widgets.
     * @param {string} layoutId
     */
    async onChangeLayout(layoutId) {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }
        this.state.dashboardLayout = layoutId;
        this.isLoading = true;

        try {
            await this.orm.write('multi.dashboards', [this.state.dashboardId], {
                dashboard_layout: layoutId
            });
            await this.applyLayoutRearrangement(layoutId);
            this.notification.add(`Layout changed to ${layoutId === 'layout_1' ? 'Centered' : layoutId === 'layout_2' ? 'Side-by-Side' : 'Grid'}`, { type: "success" });
        } catch (e) {
            console.error("Error changing layout", e);
            this.notification.add("Failed to change layout", { type: "danger" });
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Rearrange existing widgets based on the selected layout algorithm.
     * @param {string} layoutId
     */
    async applyLayoutRearrangement(layoutId) {
        if (!this.grid) return;

        this._isResponsiveRelayout = true;
        this.grid.batchUpdate();

        try {
            const widgets = await this.orm.call(
                'multi.dashboard.charts',
                'get_dashboard_widgets',
                [this.dashboardId],
            );

            if (!widgets || widgets.length === 0) return;

            // Sort widgets by their current Y position, then X position to maintain a logical order
            widgets.sort((a, b) => {
                if (a.gs_y !== b.gs_y) return a.gs_y - b.gs_y;
                return a.gs_x - b.gs_x;
            });

            let currentX = 0;
            let currentY = 0;
            let rowMaxHeight = 0;
            const updates = [];

            for (const widget of widgets) {
                let newW, newH, newX, newY;

                if (layoutId === 'layout_1') {
                    // Centered: Fixed width 8, centered in 12-column grid (x=2)
                    newW = 8;
                    newH = widget.gs_h;
                    newX = 2;
                    newY = currentY;
                    currentY += newH;
                } else if (layoutId === 'layout_2') {
                    // Side-by-Side: 2 columns of width 6
                    newW = 6;
                    newH = widget.gs_h;
                    if (currentX + newW > 12) {
                        currentX = 0;
                        currentY += rowMaxHeight;
                        rowMaxHeight = 0;
                    }
                    newX = currentX;
                    newY = currentY;
                    currentX += newW;
                    rowMaxHeight = Math.max(rowMaxHeight, newH);
                } else {
                    // Grid: 3 columns of width 4
                    newW = 4;
                    newH = widget.gs_h;
                    if (currentX + newW > 12) {
                        currentX = 0;
                        currentY += rowMaxHeight;
                        rowMaxHeight = 0;
                    }
                    newX = currentX;
                    newY = currentY;
                    currentX += newW;
                    rowMaxHeight = Math.max(rowMaxHeight, newH);
                }

                // Find the element in the grid
                const gridEl = this.gridRef.el.querySelector(`[data-record-id="${widget.id}"]`);
                if (gridEl) {
                    this.grid.update(gridEl, { x: newX, y: newY, w: newW, h: newH });
                }

                // Save the new position to DB
                updates.push(this.orm.write('multi.dashboard.charts', [widget.id], {
                    gs_x: newX,
                    gs_y: newY,
                    gs_w: newW,
                    gs_h: newH
                }));
            }

            await Promise.all(updates);
        } finally {
            this.grid.commit();
            // grid events can fire on next tick, keep guard briefly
            setTimeout(() => {
                this._isResponsiveRelayout = false;
            }, 100);
        }
    }

    /* Handle the drop of a new widget from the sidebar: open a form view
    to create the widget, then add it to the grid on save */
    async handleNewWidgetDrop(item) {
        const x = item.x !== undefined ? item.x : 0;
        const y = item.y !== undefined ? item.y : 0;

        const type = item.el.dataset.type;
        const w = item.w;
        const h = item.h;

        this.grid.removeWidget(item.el, true);
        await this._openWidgetConfigForm(type, w, h, x, y);
    }

    /**
     * Handle clicking on a widget in the sidebar (for mobile or convenience).
     * @param {Object} item
     */
    async onItemClick(item) {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }

        // On desktop (>= 992px), we force drag-and-drop.
        // Clicking is only for mobile/tablet where dragging is difficult.
        if (window.innerWidth >= 992) {
            return;
        }

        // Hide sidebar on mobile/tablet so the configuration form is visible
        if (window.innerWidth < 992) {
            this.state.sidebarVisible = false;
            if (this.grid && typeof this.grid.setStatic === 'function') {
                this.grid.setStatic(!this.state.isEditMode);
            }
        }
        // Default to (0,0); GridStack or the user can adjust later.
        await this._openWidgetConfigForm(item.type, item.w, item.h, 0, 0);
    }

    /**
     * Common logic to open the widget configuration form.
     * @param {string} type
     * @param {number} w
     * @param {number} h
     * @param {number} x
     * @param {number} y
     */
    async _openWidgetConfigForm(type, w, h, x, y) {
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
                default_gs_w: w,
                default_gs_h: h,
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
            const data = await this.orm.call('multi.dashboard.charts', 'get_widget_value', [[w.id]], { date_filter: this.state.dateFilter });

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
        if (this.grid && typeof this.grid.compact === 'function') {
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

    async summarizeDashboard() {
        if (this.state.isSummarizing) return;

        this.state.isSummarizing = true;
        this.state.aiSummary = false;

        try {
            const result = await this.orm.call(
                "multi.dashboards",
                "action_get_dashboard_summary",
                [this.dashboardId],
                { date_filter: this.state.dateFilter }
            );

            if (result && result.success) {
                // Formatting the summary to be Odoo-friendly if it's markdown
                // We'll use a simple approach here, but in a real app we might use a markdown lib
                let summary = result.summary;

                // Convert Markdown to clean HTML with basic headers support
                summary = summary
                    .replace(/### (.*?)(\n|$)/g, '<h5 class="mt-3 mb-1">$1</h5>') // H3 -> H5
                    .replace(/## (.*?)(\n|$)/g, '<h4 class="mt-4 mb-2 text-primary">$1</h4>') // H2 -> H4
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')     // Bold
                    .replace(/\* (.*?)(\n|$)/g, '<li>$1</li>')            // Bullets
                    .replace(/\n\n/g, '<br/><br/>')
                    .replace(/\n/g, '<br/>');

                // Wrap bullets in <ul> if present
                if (summary.includes('<li>')) {
                    summary = summary.replace(/(<li>.*?<\/li>)+/sg, (match) => `<ul class="ps-3 mb-0 mt-2">${match}</ul>`);
                }

                this.state.aiSummary = markup(summary);
                this.notification.add("Insights generated!", { type: "success" });
            } else {
                this.notification.add(result.error || "Failed to generate insights.", { type: "danger" });
            }
        } catch (error) {
            console.error("Error summarizing dashboard:", error);
            this.notification.add("An error occurred while generating insights.", { type: "danger" });
        } finally {
            this.state.isSummarizing = false;
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

    /**
     * Set the current date filter for the dashboard and reload all widgets.
     * @param {string} type 
     */
    async setDateFilter(type) {
        const today = new Date();
        let start_date = null;
        let end_date = null;
        let label = 'All Time';

        const formatDate = (date) => {
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, '0');
            const d = String(date.getDate()).padStart(2, '0');
            return `${y}-${m}-${d}`;
        };

        switch (type) {
            case 'today':
                start_date = formatDate(today);
                end_date = formatDate(today);
                label = 'Today';
                break;
            case 'this_week':
                const first = today.getDate() - today.getDay();
                const last = first + 6;
                start_date = formatDate(new Date(new Date().setDate(first)));
                end_date = formatDate(new Date(new Date().setDate(last)));
                label = 'This Week';
                break;
            case 'this_month':
                start_date = formatDate(new Date(today.getFullYear(), today.getMonth(), 1));
                end_date = formatDate(new Date(today.getFullYear(), today.getMonth() + 1, 0));
                label = 'This Month';
                break;
            case 'this_year':
                start_date = formatDate(new Date(today.getFullYear(), 0, 1));
                end_date = formatDate(new Date(today.getFullYear(), 11, 31));
                label = 'This Year';
                break;
            case 'all':
            default:
                start_date = null;
                end_date = null;
                label = 'All Time';
                break;
        }

        this.state.dateFilter = { label, start_date, end_date };
        localStorage.setItem(`dashboard_filter_${this.state.dashboardId}`, JSON.stringify(this.state.dateFilter));
        this.closeDateFilterDropdown();
        await this.loadWidgets();
    }

    /**
     * Apply a custom date range selected by the user.
     */
    async applyCustomDateFilter() {
        const start = this.state.customStartDate;
        const end = this.state.customEndDate;

        if (!start && !end) {
            this.notification.add("Please select at least one date for the custom range", { type: "warning" });
            return;
        }

        this.state.dateFilter = {
            label: this.getCustomDateFilterLabel(start, end),
            start_date: start,
            end_date: end
        };
        localStorage.setItem(`dashboard_filter_${this.state.dashboardId}`, JSON.stringify(this.state.dateFilter));
        this.closeDateFilterDropdown();
        await this.loadWidgets();
    }

    getCustomDateValue(value) {
        return value ? deserializeDate(value) : null;
    }

    onCustomDateChange(type, value) {
        const serializedValue = value ? serializeDate(value) : null;
        if (type === 'start') {
            this.state.customStartDate = serializedValue;
        } else {
            this.state.customEndDate = serializedValue;
        }
    }

    getCustomDateFilterLabel(start, end) {
        if (start && end) {
            return `${formatDate(deserializeDate(start))} to ${formatDate(deserializeDate(end))}`;
        }
        if (start) {
            return `From ${formatDate(deserializeDate(start))}`;
        }
        if (end) {
            return `Until ${formatDate(deserializeDate(end))}`;
        }
        return 'Custom Range';
    }

    /**
     * Clear all widgets from the dashboard after confirmation.
     */
    async clearDashboard() {
        if (!this.state.isManager) {
            this.notification.add("Access Denied: Only managers can edit layouts.", { type: "danger" });
            return;
        }

        const confirmed = await new Promise((resolve) => {
            this.env.services.dialog.add(ConfirmationDialog, {
                body: "Are you sure you want to clear all widgets from this dashboard? This action cannot be undone.",
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });

        if (!confirmed) return;

        try {
            this.state.loading = true; // Use state.loading instead of this.isLoading for UI feedback
            await this.orm.call("multi.dashboard.charts", "action_clear_dashboard", [this.state.dashboardId]);
            await this.loadWidgets();
            this.state.loading = false;
            this.notification.add("Dashboard cleared successfully.", { type: "success" });
        } catch (error) {
            console.error("Failed to clear dashboard:", error);
            this.state.loading = false;
            this.notification.add("An error occurred while clearing the dashboard.", { type: "danger" });
        }
    }

    closeDateFilterDropdown() {
        const { button, dropdown, menu } = this.getDateFilterDropdownElements();
        if (!button || !menu) {
            return;
        }

        const BootstrapDropdown = globalThis.bootstrap?.Dropdown;
        if (BootstrapDropdown) {
            BootstrapDropdown.getOrCreateInstance(button).hide();
        } else {
            menu.classList.remove('show');
            menu.removeAttribute('data-bs-popper');
            button.classList.remove('show');
            button.setAttribute('aria-expanded', 'false');
            button.blur();
            dropdown?.classList.remove('show');
        }
    }

    getDateFilterDropdownElements() {
        const button = this.dateFilterDropdownButton?.el || null;
        const dropdown = button?.closest('.dropdown') || null;
        const menu = dropdown?.querySelector('.multi-dashboard-date-dropdown') || null;
        return { button, dropdown, menu };
    }

    isDateFilterDropdownOpen() {
        const { button, menu } = this.getDateFilterDropdownElements();
        return Boolean(button && menu && button.getAttribute('aria-expanded') === 'true' && menu.classList.contains('show'));
    }

    handleDocumentPointerDown(ev) {
        if (!this.isDateFilterDropdownOpen()) {
            return;
        }

        const target = ev.target;
        const { button, menu } = this.getDateFilterDropdownElements();
        if (!(target instanceof Element)) {
            return;
        }

        if (
            button?.contains(target) ||
            menu?.contains(target) ||
            target.closest('.o_datetime_picker') ||
            target.closest('.o_popover')
        ) {
            return;
        }

        this.closeDateFilterDropdown();
    }
}

MultiDashboard.components = {
    DashboardSidebar,
    DashboardChat,
    DashboardChart,
    DashboardTileWidget,
    DashboardListWidget,
    DashboardTodoWidget,
    DashboardClock,
    DashboardProgressBar,
    DateTimeInput
};
MultiDashboard.template = "owl.MultiDashboard"
registry.category("actions").add("MultiDashboardClientAction", MultiDashboard)
