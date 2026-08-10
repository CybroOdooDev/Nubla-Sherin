/** @odoo-module **/
import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { renderToFragment } from "@web/core/utils/render";

const { fuzzyLookup } = require('@web/core/utils/search');
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";

const { onMounted, useState, onPatched } = owl;

patch(NavBar.prototype, {

    setup() {
        super.setup();
        this._search_def = null;
        this._search_timeout = null;

        let { apps, menuItems } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;
        this.state = useState({ flag: false });

        let now = new Date();
        let hour = now.getHours();
        let min = now.getMinutes();
        let start = session.infinitoDarkStart.split(':');
        let startHour = parseInt(start[0]);
        let startMin = parseInt(start[1]);
        let end = session.infinitoDarkEnd.split(':');
        let endHour = parseInt(end[0]);
        let endMin = parseInt(end[1]);

        if (startHour > endHour) {
            endHour += 24;
            if (hour < startHour) {
                hour += 24;
            }
        }

        let dark = false;
        if (endHour > hour && hour > startHour) {
            dark = true;
        } else if (hour === startHour && min >= startMin && hour < endHour) {
            dark = true;
        } else if (hour === endHour && min <= endMin && hour >= startHour) {
            dark = true;
        }

        const applyDarkMode = () => {
            // Guard: never re-add dark mode when it is globally disabled.
            // session.infinitoDark is the master switch set in theme settings.
            // Without this check, onPatched would re-enable dark-mode classes
            // whenever the current time falls inside the schedule window, even
            // after WebClient.darkModeCheck() has just called disableDark().
            if (!session.infinitoDark) {
                return;
            }
            if (dark) {
                if (!document.body.classList.contains('dark-mode')) {
                    document.body.classList.add('dark-mode');
                }
                const navbars = document.querySelectorAll('.o_navbar, .o_main_navbar, .pos-topheader');
                navbars.forEach(n => n.classList.add('dark-mode'));
                document.documentElement.classList.add('dark-mode');
                try { localStorage.setItem('infinito_dark_mode', '1'); } catch (e) {}
            }
        };

        onMounted(() => {
            this.$search_container = document.querySelector(".search-container");
            this.$search_input = document.querySelector(".search-input input");
            this.$search_results = document.querySelector(".search-results");
            this.$app_menu = document.querySelector(".app-menu");
            this.$dropdown_menu = document.querySelector(".dropdown-menu");
            // Delegated click listener on the search results container so that
            // dynamically injected result anchors (rendered via renderToFragment,
            // which cannot bind Owl component methods via t-on-click) still fire
            // onClick without causing "Invalid handler: undefined" errors.
            if (this.$search_results) {
                this.$search_results.addEventListener('click', (ev) => this.onClick(ev));
            }
            this.doGreeting();
            this.setupSidebarListeners();
            this._setupFullScreenAppsMenuListeners();
            applyDarkMode();
        });

        onPatched(() => {
            applyDarkMode();
        });
    },

    _hideNavbarMenusForFullScreenAppsMenu() {
        this._setElementsDisplay('.o_menu_sections', 'none');
        this._setElementsDisplay('.o_menu_brand', 'none');
    },

    _showNavbarMenusAfterFullScreenAppsMenu() {
        this._setElementsDisplay('.o_menu_sections', 'flex');
        this._setElementsDisplay('.o_menu_brand', 'block');
    },

    _setupFullScreenAppsMenuListeners() {
        const toggle = document.querySelector("a.full[data-bs-toggle='dropdown']");
        if (!toggle) {
            return;
        }
        toggle.addEventListener("show.bs.dropdown", () => this._hideNavbarMenusForFullScreenAppsMenu());
        toggle.addEventListener("hidden.bs.dropdown", () => {
            this._showNavbarMenusAfterFullScreenAppsMenu();
            this._clearSearch();
        });
    },

    setupSidebarListeners() {
        const openSidebar = document.getElementById('openSidebar');
        const closeSidebarButtons = document.querySelectorAll('#closeSidebar');
        const sidebarPanel = document.getElementById('sidebar_panel');

        if (openSidebar && sidebarPanel) {
            openSidebar.addEventListener('click', (e) => {
                e.preventDefault();
                sidebarPanel.classList.add('show');
                openSidebar.style.display = 'none';
                const closeSidebarBtn = document.querySelector('#openSidebar').nextElementSibling;
                if (closeSidebarBtn) {
                    closeSidebarBtn.style.display = 'block';
                }
            });
        }

        closeSidebarButtons.forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (sidebarPanel) {
                    sidebarPanel.classList.remove('show');
                }
                if (openSidebar) {
                    openSidebar.style.display = 'block';
                }
                closeBtn.style.display = 'none';
            });
        });
    },

    async doGreeting() {
        let time = new Date().getHours();
        let greetings = 'Good';

        if (time > 0 && time < 12) {
            greetings = 'Good Morning, ';
        } else if (time >= 12 && time < 16) {
            greetings = 'Good Afternoon, ';
        } else {
            greetings = 'Good Evening, ';
        }

        try {
            const sessionInfo = await rpc('/web/session/get_session_info');
            const userName = sessionInfo.name || "User";
            const userId = sessionInfo.uid;
            const baseUrl = sessionInfo['web.base.url'] || window.location.origin;

            greetings += userName;

            const greetingEl = document.querySelector('.infinito-greeting');
            if (greetingEl) {
                greetingEl.textContent = greetings;
            }

            const imgUrl = `${baseUrl}/web/image?model=res.users&field=avatar_128&id=${userId}`;
            const userImgEl = document.querySelector('.infinito-user_img');
            if (userImgEl) {
                userImgEl.setAttribute('src', imgUrl);
            }
        } catch (error) {
            console.error("Error fetching session info:", error);
        }
    },

    _clearSearch() {
        if (this.$search_input) {
            this.$search_input.value = '';
        }
        if (this.$search_results) {
            this.$search_results.innerHTML = '';
        }
        if (this.$search_container) {
            this.$search_container.classList.remove('has-results');
        }
        if (this.$app_menu) {
            this.$app_menu.classList.remove('o_hidden');
        }
    },

    _searchMenusSchedule() {
        if (this.$search_results) {
            this.$search_results.classList.remove("o_hidden");
        }
        if (this.$app_menu) {
            this.$app_menu.classList.add("o_hidden");
        }
        if (this._search_timeout) {
            clearTimeout(this._search_timeout);
        }
        this._search_timeout = setTimeout(() => {
            this._searchMenus();
        }, 50);
    },

    _searchMenus() {
        var query = this.$search_input ? this.$search_input.value : "";
        if (query === "") {
            if (this.$search_container) {
                this.$search_container.classList.remove("has-results");
            }
            if (this.$app_menu) {
                this.$app_menu.classList.remove("o_hidden");
            }
            if (this.$search_results) {
                this.$search_results.innerHTML = "";
            }
            return;
        }

        var results = [];
        fuzzyLookup(query, this._apps, (menu) => menu.label)
            .forEach((menu) => {
                let webIconData = menu.webIcon || menu.webIconData || menu.web_icon_data || menu.web_icon || null;
                if (webIconData && !webIconData.startsWith('data:image')) {
                    webIconData = "data:image/png;base64," + webIconData;
                }
                results.push({
                    category: "apps",
                    name: menu.label,
                    actionID: menu.actionID,
                    id: menu.id,
                    webIconData: webIconData,
                });
            });

        fuzzyLookup(query, this._searchableMenus, (menu) =>
            (menu.parents + " / " + menu.label).split("/").reverse().join("/")
        ).forEach((menu) => {
            results.push({
                category: "menu_items",
                name: menu.parents + " / " + menu.label,
                actionID: menu.actionID,
                id: menu.id,
            });
        });

        if (this.$search_container) {
            this.$search_container.classList.toggle("has-results", Boolean(results.length));
        }

        const render = renderToFragment("backend_theme_infinito.SearchResults", {
            results: results,
            widget: this,
        });

        if (this.$search_results) {
            this.$search_results.innerHTML = "";
            this.$search_results.appendChild(render);
        }
    },

    onClick(ev) {
        ev.preventDefault();

        let target = ev.target;
        let data;

        while (target && !target.dataset.menuId && target !== document.body) {
            target = target.parentElement;
        }

        if (target && target.dataset) {
            data = target.dataset;
        }

        if (data && data.menuId) {
            const menuId = parseInt(data.menuId);
            const menu = this.menuService.getMenu(menuId);

            if (menu) {
                this.menuService.selectMenu(menu);
                this._clearSearch();
                setTimeout(() => this._showNavbarMenusAfterFullScreenAppsMenu(), 0);

                let app = { 'appId': data.menuId };
                rpc('/theme_studio/add_recent_app', {
                    method: 'call',
                    args: [app]
                }).catch(err => {
                    console.error('Failed to add recent app:', err);
                });
            }
        }

        const sidebar = document.getElementById('sidebar_panel');
        if (sidebar) {
            sidebar.classList.remove('show');
        }

        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(dropdown => {
            dropdown.classList.remove('show');
        });
    },

    OnClickMainMenu() {
        this.state.flag = true;
        const appComponents = document.querySelector('.app_components');
        if (appComponents && getComputedStyle(appComponents).display === "none") {
            appComponents.style.display = "block";
            appComponents.style.animation = "fadeIn 250ms";
            this._setElementsDisplay('.o_menu_sections', 'none');
            this._setElementsDisplay('.o_menu_brand', 'none');
            this._setElementsDisplay('.o_action_manager', 'none');
            this._setElementsDisplay('.sidebar_panel', 'none');
        } else {
            if (appComponents) {
                appComponents.style.display = "none";
            }
            this._setElementsDisplay('.o_menu_sections', 'flex');
            this._setElementsDisplay('.o_menu_brand', 'block');
            this._setElementsDisplay('.o_action_manager', 'block');
            this._setElementsDisplay('.sidebar_panel', 'block');
        }
    },

    OnClickCloseMainMenu() {
        this.state.flag = false;
        const appComponents = document.querySelector('.app_components');
        if (appComponents) {
            appComponents.style.display = "none";
        }
        this._setElementsDisplay('.o_menu_sections', 'flex');
        this._setElementsDisplay('.o_menu_brand', 'block');
        this._setElementsDisplay('.o_action_manager', 'block');
        this._setElementsDisplay('.sidebar_panel', 'none');
    },

    OnclickFullScreenMenu() {
        const hasShow = document.querySelector('a.show');
        if (hasShow) {
            this._setElementsDisplay('.o_menu_sections', 'none');
            this._setElementsDisplay('.o_menu_brand', 'none');
        } else {
            this._setElementsDisplay('.o_menu_sections', 'flex');
            this._setElementsDisplay('.o_menu_brand', 'block');
        }
    },

    _setElementsDisplay(selector, displayValue) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = displayValue;
            el.style.setProperty('display', displayValue, 'important');
        });
    },

    get sidebarEnabled() { return session.sidebar; },
    set sidebarEnabled(val) {},
    get sidebarIcon() { return session.sidebarIcon; },
    set sidebarIcon(val) {},
    get sidebarName() { return session.sidebarName; },
    set sidebarName(val) {},
    get sidebarResize() { return session.sidebarIcon && !session.sidebarName ? 'm-sidebar' : ''; },
    set sidebarResize(val) {},
    get sidebarCompany() { return session.sidebarCompany; },
    set sidebarCompany(val) {},
    get sidebarCompanyLogo() { return session.sidebarCompany ? 'has-company' : ''; },
    set sidebarCompanyLogo(val) {},
    get sidebarUser() { return session.sidebarUser; },
    set sidebarUser(val) {},
    get FullScreenEnabled() { return session.fullscreen ? 'd-none' : ''; },
    set FullScreenEnabled(val) {},
    get fullScreenApp() { return session.fullScreenApp; },
    set fullScreenApp(val) {},
});
