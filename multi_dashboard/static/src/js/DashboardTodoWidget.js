/** @odoo-module */
import { Component, useState, useRef, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const COLORS = [
    "#ffffff", "#ff9c9c", "#f7c698", "#fde388", "#bbd7f8", "#d9a8cc",
    "#f8d6c8", "#89e1db", "#97a6f9", "#ff9ecc", "#b7edbe", "#e6dbfc"
];
const GRADIENTS = [
    "linear-gradient(135deg, #ffffff 0%, #f3f4f6 100%)",
    "linear-gradient(135deg, #ff9c9c 0%, #ee5253 100%)",
    "linear-gradient(135deg, #f7c698 0%, #ff9f43 100%)",
    "linear-gradient(135deg, #fde388 0%, #feca57 100%)",
    "linear-gradient(135deg, #bbd7f8 0%, #54a0ff 100%)",
    "linear-gradient(135deg, #d9a8cc 0%, #9b59b6 100%)",
    "linear-gradient(135deg, #f8d6c8 0%, #ff9f43 100%)",
    "linear-gradient(135deg, #89e1db 0%, #00d2d3 100%)",
    "linear-gradient(135deg, #97a6f9 0%, #5d6df0 100%)",
    "linear-gradient(135deg, #ff9ecc 0%, #e91e63 100%)",
    "linear-gradient(135deg, #b7edbe 0%, #10ac84 100%)",
    "linear-gradient(135deg, #e6dbfc 0%, #5f27cd 100%)"
];

const colorClass = [
    "class0", "class1", "class2", "class3", "class4", "class5",
    "class6", "class7", "class8", "class9", "class10", "class11"
];

/* This component represents a To-do List widget for the dashboard.
    It allows users to add, edit, delete, and mark tasks as done.
    The widget's color can be customized based on the provided data. */
export class DashboardTodoWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            // Use props data if available, otherwise empty array
            todos: this.props.data && this.props.data.todos ? this.props.data.todos : [],
            inputValue: "",
            isAdding: false,
        });
        this.inputRef = useRef("todoInput");
    }

    // Helper to get the hex code based on the prop integer
    get accentColor() {
        const index = this.props.data.todo_color || 0;
        return COLORS[index] || COLORS[0];
    }

    // Helper to get the CSS class based on the prop integer
    get colorClass() {
        const index = this.props.data.todo_color || 0;
        return colorClass[index] || colorClass[0];
    }

    get backgroundStyle() {
        const index = this.props.data.todo_color || 0;
        if (this.props.data.use_background_gradient) {
            return (GRADIENTS[index] || GRADIENTS[0]);
        }
        return '';
    }

    // Toggle the visibility of the input field for adding new tasks
    toggleInput() {
        if (this.props.isPreview) {
            return;
        }
        this.state.isAdding = !this.state.isAdding;
        if (this.state.isAdding) {
            setTimeout(() => {
                if (this.inputRef.el) this.inputRef.el.focus();
            }, 50);
        } else {
            this.state.inputValue = "";
        }
    }

    // Open the edit form for the current to-do list. Assumes that the record ID is passed in props.
    onEdit() {
        const todoId = this.props.data.id; // Assuming you pass the record ID in props
        if (!todoId) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "multi.dashboard.charts", // Your model name
            res_id: todoId,
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                // Trigger a refresh. Since this is a child,
                if (this.props.onRefresh) {
                    await this.props.onRefresh();
                }
            }
        });
    }

    // Add a new to-do item when the user presses Enter in the input field
    async addTodo(ev) {
        if (this.props.isPreview) {
            return;
        }
        if (ev.key === "Enter" && this.state.inputValue.trim()) {
            const val = this.state.inputValue;
            try {
                const result = await this.orm.create("multi.dashboard.todo", [{
                    name: val,
                    chart_id: this.props.recordId,
                    is_done: false
                }]);
                const newId = Array.isArray(result) ? result[0] : result;
                this.state.todos.unshift({
                    id: newId,
                    name: val,
                    is_done: false
                });
                this.state.inputValue = "";
                this.toggleInput()
            } catch (e) {
                console.error("Failed to create Todo", e);
            }
        }
    }

    // Toggle the completion status of a to-do item
    async toggleTodo(todo) {
        if (this.props.isPreview) {
            return;
        }
        const previousState = todo.is_done;
        todo.is_done = !todo.is_done;
        this.sortTodos();

        try {
            await this.orm.write("multi.dashboard.todo", [todo.id], {
                is_done: todo.is_done
            });
        } catch (e) {
            todo.is_done = previousState;
            this.sortTodos();
        }
    }

    // Enable editing mode for a to-do item. This will show an input field with the current name.
    editTodoTask(todo) {
        if (this.props.isPreview) {
            return;
        }
        this.state.todos.forEach(t => {
            if (t.isEditing) this.cancelEdit(t);
        });

        todo.originalName = todo.name;
        todo.isEditing = true;
    }

    // Save the edited name of a to-do item. If the name is empty, it will not save and remain in edit mode.
    async saveEdit(todo) {
        if (!todo.name.trim()) return;
        todo.isEditing = false;
        try {
            await this.orm.write("multi.dashboard.todo", [todo.id], {
                name: todo.name
            });
            delete todo.originalName;
        } catch (e) {
            todo.name = todo.originalName;
        }
    }

    // Cancel the editing of a to-do item and revert to the original name.
    cancelEdit(todo) {
        if (todo.originalName !== undefined) {
            todo.name = todo.originalName; // Revert name
            delete todo.originalName;
        }
        todo.isEditing = false;
    }

    // Delete the entire to-do list (the chart record). This will remove the widget from the dashboard.
    async deleteTodo() {
        if (this.props.isPreview) {
            return;
        }
        const todoId = this.props.recordId;
        await this.orm.unlink('multi.dashboard.charts', [todoId]).then(() => {
            // it's best to call a prop passed from MultiDashboard.
            if (this.props.onDelete) {
                this.props.onDelete();
            }
        });
    }

    // Delete a single to-do item from the list. This will remove the item from the UI and delete it from the database.
    async deleteTodoTask(todoId) {
        if (this.props.isPreview) {
            return;
        }
        const backup = [...this.state.todos];
        this.state.todos = this.state.todos.filter(t => t.id !== todoId);

        try {
            await this.orm.unlink("multi.dashboard.todo", [todoId]);
        } catch (e) {
            this.state.todos = backup;
        }
    }

    // Sort the to-do items so that incomplete tasks are shown before completed ones.
    sortTodos() {
        this.state.todos.sort((a, b) => Number(a.is_done) - Number(b.is_done));
    }

    // Trigger the download of the to-do list in JSON format.
    downloadJson() {
        this.downloadJsonExport({ chart_id: this.props.data.id });
    }

    // Call the server to get the JSON export of the to-do list and trigger a download in the browser.
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

DashboardTodoWidget.template = xml`
    <div t-attf-class="todo-widget-card h-100 overflow-hidden {{ colorClass }}"
         t-attf-style="{{ this.backgroundStyle ? 'background: ' + this.backgroundStyle + ';' : '' }}">
        <div class="todo-header">
            <div class="d-flex align-items-center">
                <span class="todo-title me-2"><t t-esc="props.data.name"/></span>
                <span class="dashboard-badge rounded-pill text-dark border" t-if="state.todos.filter(t => !t.is_done).length > 0">
                    <t t-esc="state.todos.filter(t => !t.is_done).length"/>
                </span>
            </div>
            <div t-if="!props.isPreview" class="todo-tools float-right d-flex align-items-center gap-1">
                <button class="btn-edit-todo" t-on-click="onEdit">
                    <i class="fa fa-pencil"/>
                </button>
                <button class="btn-del-todo" t-on-click="deleteTodo">
                    <i class="fa fa-trash"/>
                </button>
                <button class="btn-download-json" t-on-click="downloadJson">
                    <i class="fa fa-download"/>
                </button>
                <button class="btn-add-task" t-att-class="state.isAdding ? 'active' : ''" t-on-click="toggleInput">
                    <i class="fa fa-plus"/>
                </button>
            </div>

        </div>

        <div class="todo-input-section" t-att-class="state.isAdding ? 'show' : 'd-none'">
            <input type="text" class="form-control modern-input" placeholder="Type and press Enter..."
                   t-model="state.inputValue" t-on-keyup="addTodo" t-ref="todoInput"/>
        </div>

        <div class="flex-grow-1 overflow-auto custom-scroll" style="min-height: 0;">
            <t t-if="state.todos.length === 0">
                <div class="h-100 d-flex flex-column align-items-center justify-content-center">
                    <i class="fa fa-thumb-tack fa-2x mb-2"/>
                    <small>All caught up!</small>
                </div>
            </t>

            <ul class="list-group list-group-flush pt-2 pb-2" style="margin-bottom: 2rem;">
                <t t-foreach="state.todos" t-as="todo" t-key="todo.id">
                    <li class="d-flex align-items-center justify-content-between todo-list-item">

                        <t t-if="!todo.isEditing">
                            <div class="d-flex align-items-center flex-grow-1" style="min-width: 0;">
                                <input class="custom-todo-check me-3 flex-shrink-0" type="checkbox"
                                       t-att-checked="todo.is_done"
                                       t-on-change="() => this.toggleTodo(todo)"
                                       t-att-id="'check_' + todo.id"/>

                                <label class="todo-text text-wrap text-break user-select-none mb-0"
                                       t-att-for="'check_' + todo.id"
                                       t-att-class="todo.is_done ? 'done' : ''"
                                       style="cursor: pointer;">
                                    <t t-esc="todo.name"/>
                                </label>
                            </div>

                            <div class="task-actions d-flex align-items-center">
                                <button class="btn-edit-task me-1"
                                        t-on-click="() => this.editTodoTask(todo)"
                                        title="Edit">
                                    <i class="fa fa-pencil"/>
                                </button>
                                <button class="btn-del-task"
                                        t-on-click="() => this.deleteTodoTask(todo.id)"
                                        title="Delete">
                                    <i class="fa fa-trash-o"/>
                                </button>
                            </div>
                        </t>

                        <t t-else="">
                            <div class="d-flex align-items-center flex-grow-1 me-2">
                                <input type="text"
                                       class="form-control form-control-sm"
                                       t-model="todo.name"
                                       t-on-keydown="(ev) => ev.key === 'Enter' ? this.saveEdit(todo) : (ev.key === 'Escape' ? this.cancelEdit(todo) : null)"
                                       autofocus="autofocus"/>
                            </div>
                            <div class="d-flex align-items-center">
                                <button class="btn btn-lg btn-link text-success p-0 me-2"
                                        t-on-click="() => this.saveEdit(todo)">
                                    <i class="fa fa-check"/>
                                </button>
                                <button class="btn btn-lg btn-link text-danger p-0"
                                        t-on-click="() => this.cancelEdit(todo)">
                                    <i class="fa fa-times"/>
                                </button>
                            </div>
                        </t>
                    </li>
                </t>
            </ul>
        </div>
    </div>
`;
