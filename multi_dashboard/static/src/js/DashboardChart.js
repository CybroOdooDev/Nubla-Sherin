/** @odoo-module */
import { Component, onMounted, onWillUnmount, useRef, useEffect, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const COLORS = [
    "#ffffff", "#ff9c9c", "#f7c698", "#fde388", "#bbd7f8", "#d9a8cc",
    "#f8d6c8", "#89e1db", "#97a6f9", "#ff9ecc", "#b7edbe", "#e6dbfc"
];

// Dashboard Chart component responsible for rendering different types of charts using amCharts 5.
export class DashboardChart extends Component {
    static props = {
        id: { type: Number, optional: true },
        name: { type: String, optional: true },
        data: { type: Array, optional: true },
        series: { type: Array, optional: true },
        chartType: { type: String, optional: true },
        color: { type: Number, optional: true },
        orientation: { type: String, optional: true },
        theme: { type: String, optional: true },
        onRefresh: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        filter: { type: String, optional: true },
        modelName: { type: String, optional: true },
        groupField: { type: String, optional: true },
        subGroupField: { type: String, optional: true },
        isPreview: { type: Boolean, optional: true }
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.chartRef = useRef("chartdiv");
        this.root = null;

        onMounted(() => {
            this.renderChart();
        });

        onWillUnmount(() => {
            if (this.root) {
                this.root.dispose();
            }
        });

        useEffect(() => {
            this.renderChart();
        }, () => [this.props.data, this.props.chartType, this.props.series]);
    }

    // Main method to render the chart based on props
    renderChart() {
        if (this.root) {
            this.root.dispose();
        }

        const data = this.props.data || [];
        const type = this.props.chartType || 'bar';
        const themeKey = this.props.theme || 'default';
        this.root = am5.Root.new(this.chartRef.el);
        const themeMap = {
            'default': null,
            'material': window.am5themes_Material,
            'kelly': window.am5themes_Kelly,
            'dataviz': window.am5themes_Dataviz,
            'moonrise': window.am5themes_Moonrise,
            'frozen': window.am5themes_Frozen,
            'spiritedaway': window.am5themes_Spirited,
        };

        this.exporting = am5plugins_exporting.Exporting.new(this.root, {
            filePrefix: this.props.name || "Chart",
            dataSource: data,

            pngOptions: { quality: 0.8, maintainPixelRatio: true },
            jpgOptions: { quality: 1, maintainPixelRatio: true },
            pdfOptions: {
                addURL: false,
                imageFormat: "png",
                includeData: false,
            },
            xlsxOptions: {},
            csvOptions: { addColumnNames: true, separator: "," }
        });

        const activeThemes = [
            am5themes_Animated.new(this.root)
        ];
        const SelectedThemeClass = themeMap[themeKey];

        if (SelectedThemeClass) {
            activeThemes.push(SelectedThemeClass.new(this.root));
        } else if (themeKey !== 'default') {
            console.warn(`Theme ${themeKey} script not loaded in manifest.`);
        }
        this.root.setThemes(activeThemes);

        if (type === 'bar' || type === 'line' || type === 'stacked') {
            this._createXYChart(data, type);
        } else if (type === 'pie') {
            this._createPieChart(data, type);
        } else if (type === 'donut') {
            this._createDonutChart(data, type)
        } else if (type === 'funnel' || type === 'pyramid') {
            this._createPyramidFunnelChart(data, type);
        } else if (type === 'radar') {
            this._createRadarChart(data);
        } else if (type === 'radialBar') {
            this._createRadialBarChart(data);
        } else if (type === 'scatter') {
            this._createScatterChart(data);
        }
    }

    // Simple method to get accent color based on the provided index, defaults to first color if index is out of range or not provided.
    get accentColor() {
        const index = this.props.color || 0;
        return COLORS[index] || COLORS[0];
    }

    // Method to handle deletion of the chart record.
    onDelete() {
        const chartId = this.props.id;
        if (!chartId) return;

        this.orm.unlink('multi.dashboard.charts', [chartId]).then(() => {
            if (this.props.onDelete) {
                this.props.onDelete();
            } else if (this.props.onRefresh) {
                // Fallback for any context that only passes onRefresh
                this.props.onRefresh();
            }
        });
    }

    // Method to handle editing of the chart record.
    onEdit() {
        const chartId = this.props.id;
        if (!chartId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts",
            res_id: chartId,
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                if (this.props.onRefresh) {
                    await this.props.onRefresh();
                }
            }
        });
    }

    // Method to handle click on the chart container for settings
    onChartClick(ev) {
        if (this.props.isPreview) return;
        console.log("CLICKEDDDDDDDDDDDDDD")

        // If in edit mode (sidebar visible) and user is manager, clicking the chart opens settings
        if (this.props.isManager && this.props.sidebarVisible) {
            // Check if the chart type is one of the requested types
            const supportedTypes = ['bar', 'pie', 'donut', 'stacked'];
            if (supportedTypes.includes(this.props.chartType)) {
                this.onEdit();
            }
        }
    }

    // Method to handle drill-down for specific chart elements
    async _onChartElementClick(ev) {
        if (this.props.isPreview) return;

        console.log("Chart element interaction detected:", ev.target);

        // If in edit mode, element click also opens settings
        if (this.props.isManager && this.props.sidebarVisible) {
            this.onEdit();
            return;
        }

        const dataItem = ev.target.dataItem;
        if (!dataItem) return;

        // Determine category value from the chart's data point
        // Use raw_value if available (for precise ID filtering), otherwise fall back to formatted category
        const dataContext = dataItem.dataContext;
        const categoryValue = (dataContext && dataContext.raw_value !== undefined)
            ? dataContext.raw_value
            : (dataItem.get("category") || dataItem.get("categoryX") || dataItem.get("categoryY"));

        if (categoryValue === undefined || categoryValue === null) return;

        // Determine the field name for filtering
        const groupField = this.props.groupField;
        if (!groupField) return;

        // Build the extra domain for drill-down
        // Handle both ID-based filtering and string-based fallbacks for "Undefined"
        const extraDomain = (categoryValue === "Undefined" || categoryValue === false)
            ? [[groupField, '=', false]]
            : [[groupField, '=', categoryValue]];

        const action = await this.orm.call(
            "multi.dashboard.charts",
            "action_open_filtered_records",
            [[this.props.id]],
            {
                date_filter: this.props.filter || null,
                extra_domain: extraDomain
            }
        );

        if (action) {
            this.actionService.doAction(action);
        }
    }

    // Method to handle exporting the chart in various formats.
    onPrintImg(format) {
        if (this.props.isPreview) {
            return;
        }
        if (!this.exporting) {
            console.error("Exporting plugin not initialized");
            return;
        }

        switch (format) {
            case 'pdf':
                this.generatePDFReport();
                break;
            case 'xlsx':
                this.generateXLSXReport();
                break;
            case 'json':
                this.downloadJsonExport({ chart_id: this.props.id });
                break;
            default:
                this.exporting.download(format);
        }
    }

    // Method to call the server to get JSON export for either a chart or a dashboard, then trigger download in the browser.
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

    // This method is specifically for exporting the chart configuration as JSON, which can be used for backup or transferring settings between environments.
    async generateJsonReport() {
        try {
            const chartId = this.props.id;
            if (!chartId) return;

            // Call the python method 'export_as_json'
            // We pass the ID in the arguments list
            const jsonConfig = await this.orm.call(
                "multi.dashboard.charts",
                "export_as_json",
                [chartId],
            );

            // Create a blob and download it
            const blob = new Blob([jsonConfig], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${this.props.name || 'chart_config'}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error("Failed to export JSON:", error);
        }
    }

    // Method to generate a PDF report of the chart. It captures the chart as an image and embeds it into a PDF document using jsPDF.
    async generatePDFReport() {
        const imageData = await this.exporting.exportImage();
        if (!imageData) return;

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('p', 'mm', 'a4');

        // Define the specific smaller size
        const pageWidth = doc.internal.pageSize.getWidth();
        const targetWidth = 160; // Decreased from 180 to 120mm
        const xPosition = (pageWidth - targetWidth) / 2; // Center the image

        // Create Image object to maintain proportions
        const img = new Image();
        img.src = imageData;

        img.onload = () => {
            // Calculate height based on the new smaller width
            const targetHeight = (img.height / img.width) * targetWidth;

            doc.setFontSize(14);
            doc.text(this.props.name, xPosition, 20);

            doc.setFontSize(10);
            doc.text(`Generated on: ${new Date().toLocaleString()}`, xPosition, 25);

            doc.addImage(imageData, 'PNG', xPosition, 30, targetWidth, targetHeight);

            doc.save(this.props.name + ".pdf");
        };
    }

    // Method to generate an XLSX report of the chart data. It converts the chart data into a worksheet and triggers a download using SheetJS.
    async generateXLSXReport() {
        try {
            // 1. Get the data from the chart
            // In amCharts 5, data is usually held in the series or the main chart data object
            const chartData = this.props.data;

            if (!chartData || chartData.length === 0) {
                console.warn("No data found to export.");
                return;
            }

            const worksheet = window.XLSX.utils.json_to_sheet(chartData);

            const workbook = window.XLSX.utils.book_new();
            window.XLSX.utils.book_append_sheet(workbook, worksheet, "Chart Data");

            const fileName = `${this.props.name || 'Export'}.xlsx`;
            window.XLSX.writeFile(workbook, fileName);

        } catch (error) {
            console.error("Failed to generate XLSX report:", error);
        }
    }

    // Method to create a Radar Chart using amCharts 5.
    _createRadarChart(data) {
        const root = this.root;
        const seriesConfig = this.props.series || [{ valueField: 'value', name: 'Count' }];

        // Create Radar Chart Container
        let chart = root.container.children.push(am5radar.RadarChart.new(root, {
            panX: false,
            panY: false,
            layout: root.verticalLayout
        }));

        // X-Axis (Circular/Category)
        let xRenderer = am5radar.AxisRendererCircular.new(root, {});
        xRenderer.labels.template.setAll({
            textType: "adjusted"
        });

        let xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
            maxDeviation: 0,
            categoryField: "category",
            renderer: xRenderer,
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.data.setAll(data);

        // Y-Axis (Radial/Value)
        let yRenderer = am5radar.AxisRendererRadial.new(root, {});
        let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: yRenderer
        }));

        // Create Series (Loop for multiple measures or sub-groups)
        seriesConfig.forEach((s) => {
            let series = chart.series.push(am5radar.RadarLineSeries.new(root, {
                name: s.name,
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: s.valueField,
                categoryXField: "category",
                tooltip: am5.Tooltip.new(root, {
                    labelText: "{name}: {valueY}"
                })
            }));

            // Add bullets for data points
            series.bullets.push(function () {
                let bulletCircle = am5.Circle.new(root, {
                    radius: 5,
                    fill: series.get("fill"),
                    interactive: true,
                    cursorOverStyle: "pointer"
                });

                bulletCircle.events.on("pointerdown", (ev) => {
                    ev.originalEvent.stopPropagation();
                    this._onChartElementClick(ev);
                });

                return am5.Bullet.new(root, {
                    sprite: bulletCircle
                });
            });

            // Add click event for drill-down on strokes
            series.strokes.template.setAll({
                interactive: true,
                cursorOverStyle: "pointer"
            });
            series.strokes.template.events.on("pointerdown", (ev) => {
                ev.originalEvent.stopPropagation();
                this._onChartElementClick(ev);
            });

            // Make the lines filled with opacity for better "Spider" look
            series.strokes.template.setAll({ strokeWidth: 2 });
            series.fills.template.setAll({
                visible: true,
                fillOpacity: 0.2
            });

            series.data.setAll(data);
        });

        // Add Cursor
        let cursor = chart.set("cursor", am5radar.RadarCursor.new(root, {
            interactive: false
        }));
        cursor.lineY.set("visible", false);

        // Add Legend
        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            marginTop: 15,
            marginBottom: 15,
            layout: root.gridLayout
        }));
        legend.data.setAll(chart.series.values);

        // Animation
        chart.appear(1000, 100);
    }

    // Method to create XY Charts (Bar, Line, Stacked) using amCharts 5.
    _createXYChart(data, type) {
        const root = this.root;
        const hasSubGroup = this.props.hasSubGroup || false;

        // We stack if the explicit type is 'stacked' OR if there is a subgroup
        const shouldStack = type === 'stacked' || hasSubGroup;
        let chart = root.container.children.push(am5xy.XYChart.new(root, {
            panX: true,
            panY: false,
            wheelX: "panX",
            wheelY: "zoomX",
            layout: root.verticalLayout
        }));

        let xRenderer = am5xy.AxisRendererX.new(root, {
            minGridDistance: 30,
            cellStartLocation: 0.1,
            cellEndLocation: 0.9
        });

        xRenderer.labels.template.setAll({
            rotation: -45,
            centerY: am5.p50,
            centerX: am5.p100,
            paddingRight: 15
        });

        let xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
            categoryField: "category",
            renderer: xRenderer,
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.data.setAll(data);

        let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: am5xy.AxisRendererY.new(root, {})
        }));

        const seriesConfig = this.props.series || [{ valueField: 'value', name: 'Count' }];

        seriesConfig.forEach((s) => {
            let series;

            if (type === 'bar' || type === 'stacked') {
                series = chart.series.push(am5xy.ColumnSeries.new(root, {
                    name: s.name,
                    xAxis: xAxis,
                    yAxis: yAxis,
                    valueYField: s.valueField,
                    categoryXField: "category",
                    stacked: shouldStack,
                    tooltip: am5.Tooltip.new(root, {
                        labelText: "{name}: {valueY}"
                    })
                }));

                series.columns.template.setAll({
                    cornerRadiusTL: 5,
                    cornerRadiusTR: 5,
                    width: am5.percent(90),
                    interactive: true,
                    cursorOverStyle: "pointer"
                });

                series.columns.template.events.on("pointerdown", (ev) => {
                    ev.originalEvent.stopPropagation();
                    this._onChartElementClick(ev);
                });

                // Only apply rainbow colors if single series without stacking/sub-groups
                if (seriesConfig.length === 1 && !shouldStack) {
                    series.columns.template.adapters.add("fill", function (fill, target) {
                        return chart.get("colors").getIndex(series.columns.indexOf(target));
                    });
                    series.columns.template.adapters.add("stroke", function (stroke, target) {
                        return chart.get("colors").getIndex(series.columns.indexOf(target));
                    });
                }

            } else {
                // Line Chart
                series = chart.series.push(am5xy.LineSeries.new(root, {
                    name: s.name,
                    xAxis: xAxis,
                    yAxis: yAxis,
                    valueYField: s.valueField,
                    categoryXField: "category",
                    tooltip: am5.Tooltip.new(root, {
                        labelText: "{name}: {valueY}"
                    })
                }));

                series.strokes.template.setAll({
                    strokeWidth: 3,
                    interactive: true,
                    cursorOverStyle: "pointer"
                });

                series.strokes.template.events.on("pointerdown", (ev) => {
                    ev.originalEvent.stopPropagation();
                    this._onChartElementClick(ev);
                });

                series.bullets.push(() => {
                    let bulletCircle = am5.Circle.new(root, {
                        radius: 5,
                        fill: series.get("fill"),
                        interactive: true,
                        cursorOverStyle: "pointer"
                    });

                    bulletCircle.events.on("pointerdown", (ev) => {
                        ev.originalEvent.stopPropagation();
                        this._onChartElementClick(ev);
                    });

                    return am5.Bullet.new(root, {
                        sprite: bulletCircle
                    });
                });
            }
            series.data.setAll(data);
        });

        // Always show legend if multiple series OR if stacked/has sub-groups
        if (seriesConfig.length > 1 || shouldStack) {
            let legend = chart.children.push(am5.Legend.new(root, {
                centerX: am5.p50,
                x: am5.p50,
                marginTop: 15
            }));
            legend.data.setAll(chart.series.values);
        }

        chart.set("cursor", am5xy.XYCursor.new(root, {
            behavior: "zoomX",
            interactive: true
        }));
    }

    // Method to create either a Donut Chart or a Nested Donut Chart based on the provided data and series configuration.
    _createDonutChart(data, type) {
        const root = this.root;
        const seriesConfig = this.props.series || [{ valueField: 'value', name: 'Count' }];

        // Create the Chart Container
        let chart = root.container.children.push(am5percent.PieChart.new(root, {
            layout: root.verticalLayout,
            innerRadius: am5.percent(type === 'donut' ? 20 : 0)
        }));

        // Logic for Nested Rings
        const isNested = seriesConfig.length > 1;
        let currentRadius = type === 'donut' ? 20 : 0;
        const maxRadius = 100;
        const step = (maxRadius - currentRadius) / seriesConfig.length;

        seriesConfig.forEach((s, index) => {
            // Calculate specific radii for this ring if nested
            let seriesSettings = {
                valueField: s.valueField,
                categoryField: "category",
                alignLabels: true,
                name: s.name,
            };

            if (isNested) {
                // Calculate Start/End radius for this specific ring
                const innerR = currentRadius;
                const outerR = currentRadius + step;

                seriesSettings.innerRadius = am5.percent(innerR);
                seriesSettings.radius = am5.percent(outerR - 1); // -1 for gap
                currentRadius += step;
            }

            // Create the Series
            let series = chart.series.push(am5percent.PieSeries.new(root, seriesSettings));
            series.data.setAll(data);

            if (isNested) {
                // Only show labels on the outermost ring
                if (index !== seriesConfig.length - 1) {
                    series.labels.template.set("forceHidden", true);
                    series.ticks.template.set("forceHidden", true);
                }
            }

            series.slices.template.setAll({
                tooltipText: "{name} ({category}): {value}",
                interactive: true,
                cursorOverStyle: "pointer"
            });
            series.slices.template.events.on("pointerdown", (ev) => {
                ev.originalEvent.stopPropagation();
                this._onChartElementClick(ev);
            });
        });

        // Legend
        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            marginTop: 15,
            marginBottom: 15,
            layout: root.verticalLayout
        }));

        // Set legend data from all series, not just the first one
        if (isNested) {
            legend.data.setAll(chart.series.values);
        } else {
            // For single ring, use the original approach
            if (chart.series.length > 0) {
                legend.data.setAll(chart.series.getIndex(0).dataItems);
            }
        }
    }

    // Method to create a Pie Chart using amCharts 5.
    _createPieChart(data, type) {
        const root = this.root;

        const valueField = (this.props.series && this.props.series[0])
            ? this.props.series[0].valueField
            : 'value';

        let chart = root.container.children.push(am5percent.PieChart.new(root, {
            layout: root.verticalLayout,
            innerRadius: type === 'donut' ? am5.percent(50) : 0
        }));

        let series = chart.series.push(am5percent.PieSeries.new(root, {
            valueField: valueField,
            categoryField: "category",
            alignLabels: true,
            interactive: true
        }));

        series.slices.template.set("cursorOverStyle", "pointer");
        series.slices.template.events.on("pointerdown", (ev) => {
            ev.originalEvent.stopPropagation();
            this._onChartElementClick(ev);
        });

        series.data.setAll(data);

        series.labels.template.setAll({
            textType: "radial",
            centerX: 0,
            centerY: 0
        });

        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            marginTop: 15,
            marginBottom: 15,
            layout: root.verticalLayout,
        }));

        legend.data.setAll(series.dataItems);
    }

    // Method to create either a Funnel Chart or a Pyramid Chart based on the provided type and data.
    _createPyramidFunnelChart(data, type) {
        const root = this.root;

        // Create chart
        let chart = root.container.children.push(
            am5percent.SlicedChart.new(root, {})
        );

        const chartOrientation = this.props.orientation || 'vertical';

        // Create series
        let series;
        if (type === 'funnel') {
            series = chart.series.push(
                am5percent.FunnelSeries.new(root, {
                    alignLabels: true,
                    orientation: chartOrientation,
                    valueField: "value",
                    categoryField: "category",
                    valueIs: "height"
                })
            );
        } else {
            series = chart.series.push(
                am5percent.PyramidSeries.new(root, {
                    alignLabels: true,
                    orientation: chartOrientation,
                    valueField: "value",
                    categoryField: "category",
                    valueIs: "height"
                })
            );
        }

        series.data.setAll(data);

        // Configure appearance
        series.slices.template.setAll({
            strokeWidth: 1,
            stroke: am5.color(0xffffff),
            cornerRadius: 5,
            interactive: true,
            cursorOverStyle: "pointer"
        });

        series.slices.template.events.on("pointerdown", (ev) => {
            ev.originalEvent.stopPropagation();
            this._onChartElementClick(ev);
        });

        series.labels.template.setAll({
            fontSize: 12,
            text: "{category}: {value}"
        });

        series.ticks.template.setAll({
            strokeOpacity: 0.5,
            strokeDasharray: [2, 2]
        });

        // Add legend
        let legend = chart.children.push(
            am5.Legend.new(root, {
                marginTop: 15,
                layout: root.verticalLayout
            })
        );

        legend.data.setAll(series.dataItems);

        // Animate on load
        series.appear(1000, 100);
    }

    // Method to create a Radial Bar Chart using amCharts 5. This chart type is a circular version of a bar chart, where categories are arranged around a circle and values extend radially from the center.
    _createRadialBarChart(data) {
        const root = this.root;
        const seriesConfig = this.props.series || [{ valueField: 'value', name: 'Count' }];

        // 1. Create Chart
        let chart = root.container.children.push(am5radar.RadarChart.new(root, {
            panX: false,
            panY: false,
            innerRadius: am5.percent(20),
            layout: root.verticalLayout
        }));

        // 2. X-Axis (Circular/Category) - Categories go around the circle
        let xRenderer = am5radar.AxisRendererCircular.new(root, {
            minGridDistance: 30
        });

        // Adjust labels to face outward
        xRenderer.labels.template.setAll({
            textType: "adjusted",
            paddingTop: 10,
            radius: 10
        });

        let xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
            maxDeviation: 0,
            categoryField: "category",
            renderer: xRenderer,
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.data.setAll(data);

        // 3. Y-Axis (Radial/Value) - Values go from Center -> Out
        let yRenderer = am5radar.AxisRendererRadial.new(root, {
            minGridDistance: 30
        });

        let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: yRenderer
        }));

        // 4. Create Series
        seriesConfig.forEach((s) => {
            let series = chart.series.push(am5radar.RadarColumnSeries.new(root, {
                name: s.name,
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: s.valueField,
                categoryXField: "category",
                tooltip: am5.Tooltip.new(root, {
                    labelText: "{name}: {valueY}"
                })
            }));

            series.columns.template.setAll({
                cornerRadius: 5,
                tooltipText: "{categoryX}: {valueY}",
                width: am5.percent(90),
                interactive: true,
                cursorOverStyle: "pointer"
            });

            series.columns.template.events.on("pointerdown", (ev) => {
                ev.originalEvent.stopPropagation();
                this._onChartElementClick(ev);
            });

            // Colorize each slice differently (Rainbow effect)
            series.columns.template.adapters.add("fill", function (fill, target) {
                return chart.get("colors").getIndex(series.columns.indexOf(target));
            });
            series.columns.template.adapters.add("stroke", function (stroke, target) {
                return chart.get("colors").getIndex(series.columns.indexOf(target));
            });

            series.data.setAll(data);
        });

        // 5. Cursor
        let cursor = chart.set("cursor", am5radar.RadarCursor.new(root, {}));
        cursor.lineY.set("visible", false);

        // 6. Animation
        chart.appear(1000, 100);
    }

    // Method to create a Scatter Chart using amCharts 5.
    _createScatterChart(data) {
        const root = this.root;
        const seriesConfig = this.props.series || [{ valueField: 'value', name: 'Count' }];

        // Create XY Chart
        let chart = root.container.children.push(am5xy.XYChart.new(root, {
            panX: false,
            panY: false,
            layout: root.verticalLayout
        }));

        // Create Cursor
        let cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
            behavior: "none"
        }));
        cursor.lineY.set("visible", false);

        // Create Axes
        // X-Axis (Category - based on your grouping)
        let xRenderer = am5xy.AxisRendererX.new(root, {
            minGridDistance: 30,
            cellStartLocation: 0.1,
            cellEndLocation: 0.9
        });

        xRenderer.labels.template.setAll({
            rotation: -45,
            centerY: am5.p50,
            centerX: am5.p100,
            paddingRight: 15
        });

        let xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
            categoryField: "category",
            renderer: xRenderer,
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.data.setAll(data);

        // Y-Axis (Value)
        let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: am5xy.AxisRendererY.new(root, {})
        }));

        // Create Series (Scatter Logic)
        seriesConfig.forEach((s) => {
            let series = chart.series.push(am5xy.LineSeries.new(root, {
                name: s.name,
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: s.valueField,
                categoryXField: "category",
                tooltip: am5.Tooltip.new(root, {
                    labelText: "{name}: {valueY}"
                })
            }));

            // IMPORTANT: Hide the line stroke to make it a scatter plot
            series.strokes.template.set("strokeOpacity", 0);

            // Add Bullets (The dots)
            series.bullets.push(() => {
                let bulletCircle = am5.Circle.new(root, {
                    radius: 6, // Slightly larger than line chart bullets
                    fill: series.get("fill"),
                    stroke: root.interfaceColors.get("background"),
                    strokeWidth: 2,
                    interactive: true,
                    cursorOverStyle: "pointer"
                });

                bulletCircle.events.on("pointerdown", (ev) => {
                    ev.originalEvent.stopPropagation();
                    this._onChartElementClick(ev);
                });

                return am5.Bullet.new(root, {
                    sprite: bulletCircle
                });
            });

            // Randomize colors if it's a simple count chart
            if (seriesConfig.length === 1) {
                series.bullets.push(function () {
                    let bulletCircle = am5.Circle.new(root, {
                        radius: 6,
                        fill: chart.get("colors").getIndex(
                            series.dataItems.indexOf(series.dataItems[series.dataItems.length - 1])
                        ),
                        interactive: true,
                        cursorOverStyle: "pointer"
                    });

                    bulletCircle.events.on("pointerdown", (ev) => {
                        ev.originalEvent.stopPropagation();
                        this._onChartElementClick(ev);
                    });

                    return am5.Bullet.new(root, {
                        sprite: bulletCircle
                    });
                });
            }
            series.data.setAll(data);
        });

        // Legend
        if (seriesConfig.length > 1) {
            let legend = chart.children.push(am5.Legend.new(root, {
                centerX: am5.p50,
                x: am5.p50,
                marginTop: 15
            }));
            legend.data.setAll(chart.series.values);
        }

        // Animation
        chart.appear(1000, 100);
    }

}

DashboardChart.template = xml`
    <div class="o_dashboard_chart_container"
         t-attf-style="--widget-accent: {{ this.accentColor }};"
         t-on-pointerdown="onChartClick">

        <div class="chart-header d-flex justify-content-between align-items-center">
            <t t-esc="props.name || 'Untitled Chart'"/>
            <div class="chart-tools">
                <div class="export-group">
                    <div class="exp-print-tool main-trigger">
                        <i class="fa fa-download"/>
                    </div>
                    <div class="export-options">
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('png')" title="PNG"><i class="fa fa-picture-o"/></div>
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('jpg')" title="JPG"><i class="fa fa-file-image-o"/></div>
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('pdf')" title="PDF"><i class="fa fa-file-pdf-o"/></div>
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('xlsx')" title="Excel"><i class="fa fa-file-excel-o"/></div>
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('csv')" title="CSV"><i class="fa fa-file-text-o"/></div>
                        <div class="exp-print-tool" t-on-click="() => this.onPrintImg('json')" title="JSON"><i class="fa fa-files-o"/></div>
                    </div>
                </div>
                <div class="chart-tool o-chart-edit" t-on-click.stop="onEdit">
                    <i class="fa fa-pencil"/>
                </div>
                <div class="chart-tool o-chart-edit" t-on-click.stop="onDelete">
                    <i class="fa fa-trash"/>
                </div>
            </div>
        </div>

        <div class="chart-canvas"
             t-ref="chartdiv"
             style="width: 100%; flex-grow: 1; min-height: 300px;">
        </div>
    </div>
`;
