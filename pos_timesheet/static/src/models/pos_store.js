/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    get employeeIsAdmin() {
        const cashier = this.getCashier?.();
        return !!cashier && cashier._role === "manager";
    },

    setup() {
        this.workedTime = [];
        return super.setup(...arguments);

    },

    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.config.module_pos_hr && this.config.time_log) {
            this.timesheet = loadedData['account.analytic.line'];
            this.workedTime = [];

            if (Array.isArray(this.timesheet)) {
                this.timesheet.forEach((data) => {
                    const cashierId = data.employee_id?.[0];
                    const minutes = Math.floor((data.unit_amount || 0) * 60);
                    if (!cashierId || minutes <= 0) {
                        return;
                    }

                    const existingEntry = this.workedTime.find((entry) => entry.cashierId === cashierId);
                    if (existingEntry) {
                        existingEntry.minutes += minutes;
                    } else {
                        this.workedTime.push({ cashierId, minutes });
                    }
                });
            }

            const timesheetData = this.getStoredTimesheetData();
            timesheetData.forEach(data => {
                const pendingMinutes = this.getPendingWorkedMinutes(data);
                if (data.cashierId && pendingMinutes > 0) {
                    const existingEntry = this.workedTime.find(entry => entry.cashierId === data.cashierId);
                    if (existingEntry) {
                        existingEntry.minutes += pendingMinutes;
                    } else {
                        this.workedTime.push({ cashierId: data.cashierId, minutes: pendingMinutes });
                    }
                }
            });
            this.ensureActiveCashierTimesheet();
        }
    },

    async closePos() {
        if (this.config.module_pos_hr && this.config.time_log) {
            const data = this.prepareTimesheet();
            try {
                await this.sendTimesheet(data);

                if (this.pos_session?.task_id) {
                    try {
                        const action = await this.env.services.orm.call(
                            'pos.session',
                            'show_time_log',
                            [this.pos_session?.id || this.config?.current_session_id?.id || this.config?.current_session_id]
                        );
                        if (action && this.env.services.action) {
                            await this.env.services.action.doAction(action);
                        }
                    } catch (error) {
                        console.error("Error triggering time log view:", error);
                    }
                }

                this.workedTime = [];
                localStorage.setItem('timesheetData', JSON.stringify([]));
            } catch (error) {
                console.error("Error in closePos:", error);
            }
        }
        return super.closePos(...arguments);
    },

    resetCashier() {
        if (this.config.module_pos_hr && this.config.time_log) {
            return this._handleTimesheet(() => super.resetCashier(...arguments));
        }
        return super.resetCashier(...arguments);
    },

    setCashier(employee) {
        if (this.config.module_pos_hr && this.config.time_log) {
            return this._handleTimesheet(() => super.setCashier(...arguments), employee);
        }
        return super.setCashier(...arguments);
    },

    async _handleTimesheet(callback, employee = null) {
        try {
            const activeCashierId = this.cashier?.id;
            const data = this.prepareTimesheet(activeCashierId);
            if (data && data.length > 0 && (this.pos_session?.id || this.config?.current_session_id)) {
                await this.sendTimesheet(data);
            }
            this.setTimesheet([], employee);
        } catch (error) {
            console.error("Error in _handleTimesheet:", error);
        } finally {
            callback();
        }
    },

    setTimesheet(timesheetData, employee = null) {
        try {
            let existingData = this.getStoredTimesheetData();

            if (Array.isArray(timesheetData)) {
                timesheetData.forEach(newEntry => {
                    if (newEntry.cashierId && newEntry.workMinutes) {
                        const existingEntryIndex = existingData.findIndex(
                            entry => entry.cashierId === newEntry.cashierId &&
                                entry.sessionId === newEntry.sessionId
                        );
                        if (existingEntryIndex !== -1) {
                            existingData[existingEntryIndex].workMinutes += newEntry.workMinutes;
                            existingData[existingEntryIndex].checkOutTime = newEntry.checkOutTime;
                        } else {
                            existingData.push(newEntry);
                        }
                    }
                });
            }

            if (employee) {
                existingData = existingData.filter(
                    entry => !(entry.cashierId === employee.id && entry.sessionId === (this.pos_session?.id ||
                        this.config?.current_session_id?.id || this.config?.current_session_id) && !entry.checkOutTime)
                );
                existingData.push({
                    cashierId: employee.id,
                    checkInTime: Date.now(),
                    sessionId: this.pos_session?.id || this.config?.current_session_id?.id,
                    syncedMinutes: 0,
                });
            }

            localStorage.setItem('timesheetData', JSON.stringify(existingData));
        } catch (error) {
            console.error("Error in setTimesheet:", error);
        }
    },

    async sendTimesheet(timesheetData) {
        if (!timesheetData || !Array.isArray(timesheetData)) {
            return null;
        }

        const validTimesheetData = timesheetData.filter(data => data.workMinutes > 0).map(data => ({
            cashierId: data.cashierId,
            workMinutes: data.workMinutes,
            checkInTime: data.checkInTime,
            sessionId: data.sessionId || (this.pos_session?.id ||
                this.config?.current_session_id?.id || this.config?.current_session_id),
        }));
        if (validTimesheetData.length === 0) {
            return null;
        }
        console.log("Timesheet: Sending data to server:", validTimesheetData);
        try {
            await this.env.services.orm.call(
                'pos.session',
                'set_timesheet',
                [[this.pos_session?.id || this.config?.current_session_id?.id], validTimesheetData],
            );

            const storedTimesheetData = this.getStoredTimesheetData();
            validTimesheetData.forEach(data => {
                const index = this.workedTime.findIndex(item => item.cashierId === data.cashierId);
                if (index !== -1) {
                    this.workedTime[index].minutes += data.workMinutes;
                } else {
                    this.workedTime.push({
                        cashierId: data.cashierId,
                        minutes: data.workMinutes
                    });
                }

                const storedEntry = storedTimesheetData.find(entry =>
                    entry.cashierId === data.cashierId &&
                    entry.checkInTime === data.checkInTime &&
                    entry.sessionId === data.sessionId
                );
                if (storedEntry) {
                    storedEntry.syncedMinutes = (storedEntry.syncedMinutes || 0) + data.workMinutes;
                }
            });
            localStorage.setItem('timesheetData', JSON.stringify(storedTimesheetData));
        } catch (error) {
            console.error("Failed to send timesheet:", error);
            throw error;
        }
    },

    prepareTimesheet(cashierId = null) {
        const timesheetData = this.getStoredTimesheetData();
        if (timesheetData.length === 0) return null;

        const activeEntry = [...timesheetData].reverse().find(entry =>
            !entry.checkOutTime &&
            (!cashierId || entry.cashierId === cashierId) &&
            entry.sessionId === (this.pos_session?.id || this.config?.current_session_id?.id ||
                this.config?.current_session_id)
        );
        if (activeEntry) {
            activeEntry.checkOutTime = Date.now();
            const timeDiff = activeEntry.checkOutTime - activeEntry.checkInTime;
            activeEntry.workMinutes = Math.floor(timeDiff / (1000 * 60));
            localStorage.setItem('timesheetData', JSON.stringify(timesheetData));
        }

        return timesheetData
            .map(data => {
                const pendingMinutes = this.getPendingWorkedMinutes(data);
                if (pendingMinutes <= 0) {
                    return null;
                }
                return {
                    cashierId: data.cashierId,
                    workMinutes: pendingMinutes,
                    checkInTime: data.checkInTime,
                    sessionId: data.sessionId,
                };
            })
            .filter(data => data && data.workMinutes > 0);
    },

    getStoredTimesheetData() {
        try {
            return JSON.parse(localStorage.getItem('timesheetData')) || [];
        } catch {
            return [];
        }
    },

    ensureActiveCashierTimesheet() {
        const cashierId = this.cashier?.id;
        const sessionID = this.pos_session?.id || this.config?.current_session_id?.id;
        if (!cashierId || !sessionID) {
            console.warn("Timesheet: Missing cashierId or sessionId", { cashierId, sessionID });
            return;
        }

        const timesheetData = this.getStoredTimesheetData();
        const hasActiveEntry = timesheetData.some(entry =>
            entry.cashierId === cashierId &&
            entry.sessionId === (this.pos_session?.id || this.config?.current_session_id?.id) &&
            entry.checkInTime &&
            !entry.checkOutTime
        );

        if (!hasActiveEntry) {
            timesheetData.push({
                cashierId,
                checkInTime: Date.now(),
                sessionId: this.pos_session?.id || this.config?.current_session_id?.id,
                syncedMinutes: 0,
            });
            localStorage.setItem('timesheetData', JSON.stringify(timesheetData));
        }
    },

    getPendingWorkedMinutes(entry) {
        if (!entry?.workMinutes) {
            return 0;
        }
        return Math.max(0, entry.workMinutes - (entry.syncedMinutes || 0));
    },

    getActiveTimesheetEntry(cashierId = this.cashier?.id) {
        if (!cashierId || !this.config?.current_session_id?.id) {
            return null;
        }
        const timesheetData = this.getStoredTimesheetData();
        return [...timesheetData].reverse().find(entry =>
            entry.cashierId === cashierId &&
            entry.sessionId === (this.pos_session?.id || this.config?.current_session_id?.id) &&
            entry.checkInTime &&
            !entry.checkOutTime
        ) || null;
    },

    async syncActiveTimesheet() {
        const activeEntry = this.getActiveTimesheetEntry();
        if (!activeEntry?.checkInTime) {
            return;
        }

        const elapsedMinutes = Math.floor((Date.now() - activeEntry.checkInTime) / (1000 * 60));
        const pendingMinutes = elapsedMinutes - (activeEntry.syncedMinutes || 0);
        if (pendingMinutes <= 0) {
            return;
        }

        await this.sendTimesheet([{
            cashierId: activeEntry.cashierId,
            workMinutes: pendingMinutes,
            checkInTime: activeEntry.checkInTime,
            sessionId: activeEntry.sessionId,
        }]);
    }
});
