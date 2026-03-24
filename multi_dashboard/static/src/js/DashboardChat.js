/** @odoo-module */
import { Component, useState, useRef, useEffect, onRendered } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * AI Chat Assistant for Dashboard
 * Provides context-aware answers based on dashboard data
 */
export class DashboardChat extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.chatScrollRef = useRef("chatScroll");

        this.state = useState({
            isOpen: false,
            isLoading: false,
            inputValue: "",
            messages: [
                {
                    role: "assistant",
                    content: "Hello! I'm your Dashboard AI Assistant. Ask me anything about your data.....",
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
            ]
        });

        // Auto-scroll to bottom on new messages
        onRendered(() => {
            if (this.chatScrollRef.el) {
                this.chatScrollRef.el.scrollTop = this.chatScrollRef.el.scrollHeight;
            }
        });
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
    }

    async sendMessage() {
        const query = this.state.inputValue.trim();
        if (!query || this.state.isLoading) return;

        // Add user message to UI
        const userMsg = {
            role: "user",
            content: query,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        this.state.messages.push(userMsg);
        this.state.inputValue = "";
        this.state.isLoading = true;

        try {
            // Call backend with dashboard context
            const result = await this.orm.call(
                "multi.dashboards",
                "action_chat_with_dashboard",
                [this.props.dashboardId, query],
                {
                    chat_history: this.state.messages.slice(-10), // Send last 10 messages for context
                    date_filter: this.props.dateFilter
                }
            );

            if (result && result.success) {
                this.state.messages.push({
                    role: "assistant",
                    content: result.response,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                });
            } else {
                this.notification.add(result.error || "AI failed to respond", { type: "danger" });
            }
        } catch (error) {
            console.error("Chat error:", error);
            this.notification.add("Connection error", { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    onInputKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            this.sendMessage();
        }
    }
}

DashboardChat.template = "multi_dashboard.DashboardChat";
DashboardChat.props = {
    dashboardId: { type: Number },
    dateFilter: { type: Object, optional: true }
};
