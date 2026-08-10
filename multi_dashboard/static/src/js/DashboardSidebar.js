/** @odoo-module **/
import { Component } from "@odoo/owl";

export class DashboardSidebar extends Component {
    static props = ["*"];
    setup() {
        this.items = [
            {
                id: 'clock', name: "Clock",
                img: "clock.png",
                type: "clock",
                w: 2, h: 2,
            },
            {
                id: 'tile', name: "Tile",
                img: "tile.png",
                type: "tile",
                w: 2, h: 2,
            },
            {
                id: 'todo', name: "ToDo List",
                img: "todo.png",
                type: "todo",
                w: 2, h: 2,
            },
            {
                id: 'list',
                name: "List View",
                img: "list.png",
                type: "list",
                w: 2, h: 2,
            },
            {
                id: 'bar',
                name: "Bar Chart",
                img: "bar.png",
                type: "bar",
                w: 2, h: 2,
            },
            {
                id: 'line',
                name: "Line Chart",
                img: "line.png",
                type: "line",
                w: 2, h: 2,
            },
            {
                id: 'pie',
                name: "Pie Chart",
                img: "pie.png",
                type: "pie",
                w: 2, h: 2,
            },
            {
                id: 'donut',
                name: "Donut Chart",
                img: "donut.png",
                type: "donut",
                w: 2, h: 2,
            },
            {
                id: 'pyramid',
                name: "Pyramid Chart",
                img: "pyramid.png",
                type: "pyramid",
                w: 2, h: 2,
            },
            {
                id: 'funnel',
                name: "Funnel Chart",
                img: "funnel.png",
                type: "funnel",
                w: 2, h: 2,
            },
            {
                id: 'radar',
                name: "Radar Chart",
                img: "radar.png",
                type: "radar",
                w: 2, h: 2,
            },
            {
                id: 'stacked',
                name: "Stacked Column Chart",
                img: "stacked-col.png",
                type: "stacked",
                w: 2, h: 2,
            },
            {
                id: 'radialBar',
                name: "Radial Bar Chart",
                img: "radial.png",
                type: "radialBar",
                w: 2, h: 2,
            },
            {
                id: 'scatter',
                name: "Scatter Chart",
                img: "scatter.png",
                type: "scatter",
                w: 2, h: 2,
            },
            {
                id: 'progress',
                name: "Progress Bar",
                img: "progress.png",
                type: "progress",
                w: 2, h: 2,
            },
        ];
    }
}
DashboardSidebar.template = "owl.DashboardSidebar";
