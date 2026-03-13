/** @odoo-module */
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useState, onWillStart, useExternalListener, onWillUnmount } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

function formatDuration(totalMinutes) {
    const safeMinutes = Math.max(0, totalMinutes || 0);
    const hours = Math.floor(safeMinutes / 60);
    const minutes = safeMinutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);

        this.state = useState({
            currentSessionTime: "00:00",
            totalWorkedTime: "00:00"
        });

        this.beforeUnload = () => {
            try {
                const existingData = this.getTimesheetData();
                const lastEntry = this.getActiveEntry(this.pos.cashier?.id, existingData);

                if (lastEntry && !lastEntry.checkOutTime) {
                    lastEntry.checkOutTime = Date.now();
                    const timeDiff = lastEntry.checkOutTime - lastEntry.checkInTime;
                    lastEntry.workMinutes = Math.floor(timeDiff / (1000 * 60));
                    localStorage.setItem('timesheetData', JSON.stringify(existingData));
                }
            } catch (error) {
                console.error("Error in beforeUnload:", error);
            }
        };

        this.updateDisplayedTimes = () => {
            if (!this.pos.cashier || !this.pos.config) {
                return;
            }
            if (typeof this.pos.ensureActiveCashierTimesheet === 'function') {
                this.pos.ensureActiveCashierTimesheet();
            }
            this.state.currentSessionTime = this.workedTime;
            this.state.totalWorkedTime = this.totalWorkedTime;
        };

        onWillStart(async () => {
            if (this.pos.cashier) {
                await this.initializeTimeTracking();
            }
        });
        onWillUnmount(() => {
            if (this.timeUpdateInterval) {
                clearInterval(this.timeUpdateInterval);
            }
            if (this.timeSyncInterval) {
                clearInterval(this.timeSyncInterval);
            }
        });
        useExternalListener(window, 'beforeunload', this.beforeUnload);
    },

    initializeTimeTracking() {
        try {
            if (!this.pos.workedTime) {
                this.pos.workedTime = [];
            }

            if (typeof this.pos.ensureActiveCashierTimesheet === 'function') {
                this.pos.ensureActiveCashierTimesheet();
            }

            this.updateDisplayedTimes();
            this.timeUpdateInterval = setInterval(this.updateDisplayedTimes, 1000);
            this.timeSyncInterval = setInterval(() => {
                if (typeof this.pos.syncActiveTimesheet === 'function') {
                    this.pos.syncActiveTimesheet().catch((error) => {
                        console.error("Error syncing active timesheet:", error);
                    });
                }
            }, 60000);
        } catch (error) {
            console.error("Error initializing time tracking:", error);
        }
    },

    get checkInTime() {
        try {
            const cashierId = this.pos.cashier?.id;
            const activeEntry = cashierId ? this.getActiveEntry(cashierId) : null;
            if (!activeEntry?.checkInTime) {
                return "--:--";
            }
            return new Intl.DateTimeFormat('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            }).format(activeEntry.checkInTime);
        } catch (error) {
            console.error("Error in checkInTime:", error);
            return "--:--";
        }
    },

    get workedTime() {
        try {
            if (!this.pos.cashier) {
                return "00:00";
            }
            return formatDuration(this.calculateCurrentSessionMinutes());
        } catch (error) {
            console.error("Error in workedTime:", error);
            return "00:00";
        }
    },


    get totalWorkedTime() {
        try {
            const cashierId = this.pos.cashier?.id;
            if (!cashierId) return '00:00';

            const totalMinutes = this.calculateTotalWorkedMinutes(cashierId) +
                this.calculateUnsyncedActiveMinutes(cashierId);

            const hours = Math.floor(totalMinutes / 60);
            const minutes = totalMinutes % 60;
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
        } catch (error) {
            console.error("Error in totalWorkedTime:", error);
            return "00:00";
        }
    },

    getTimesheetData() {
        try {
            return JSON.parse(localStorage.getItem('timesheetData')) || [];
        } catch (error) {
            console.error("Error reading timesheet data:", error);
            return [];
        }
    },

    isClockInActive() {
        try {
            if (!this.pos.cashier) return false;
            const activeEntry = this.getActiveEntry(this.pos.cashier.id);
            return !!(activeEntry?.checkInTime && !activeEntry?.checkOutTime);
        } catch (error) {
            console.error("Error in isClockInActive:", error);
            return false;
        }
    },

    calculateCurrentSessionMinutes() {
        try {
            const cashierId = this.pos.cashier?.id;
            if (!cashierId) return 0;
            const activeEntry = this.getActiveEntry(cashierId);

            if (!activeEntry?.checkInTime || activeEntry?.checkOutTime) {
                return 0;
            }

            const currentTime = Date.now();
            const differenceMs = currentTime - activeEntry.checkInTime;
            return Math.floor(differenceMs / (1000 * 60));
        } catch (error) {
            console.error("Error in calculateCurrentSessionMinutes:", error);
            return 0;
        }
    },

    calculateTotalWorkedMinutes(cashierId) {
        try {
            const accumulatedEntry = this.pos.workedTime?.find(
                (entry) => entry.cashierId === cashierId
            );
            return Math.max(0, accumulatedEntry?.minutes || 0);
        } catch (error) {
            console.error("Error in calculateTotalWorkedMinutes:", error);
            return 0;
        }
    },

    calculateUnsyncedActiveMinutes(cashierId) {
        try {
            const activeEntry = this.getActiveEntry(cashierId);
            if (!activeEntry?.checkInTime || activeEntry?.checkOutTime) {
                return 0;
            }

            const elapsedMinutes = Math.floor((Date.now() - activeEntry.checkInTime) / (1000 * 60));
            return Math.max(0, elapsedMinutes - (activeEntry.syncedMinutes || 0));
        } catch (error) {
            console.error("Error in calculateUnsyncedActiveMinutes:", error);
            return 0;
        }
    },

    getActiveEntry(cashierId, timesheetData = null) {
        const sessionID = this.pos.pos_session?.id || this.pos.config?.current_session_id?.id || this.pos.config?.current_session_id;
        if (!cashierId || !sessionID) {
            return null;
        }
        const entries = timesheetData || this.getTimesheetData();
        return [...entries].reverse().find(entry =>
            entry.cashierId === cashierId &&
            entry.sessionId === sessionID &&
            entry.checkInTime &&
            !entry.checkOutTime
        ) || null;
    },
});
