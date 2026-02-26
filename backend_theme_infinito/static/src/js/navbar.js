/** @odoo-module **/
// Import necessary components and functionalities from Odoo libraries
import { NavBar } from "@web/webclient/navbar/navbar";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { WebClient } from "@web/webclient/webclient";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import InfinitoRecentApps from './recentApps';
import MenuBookmark from 'backend_theme_infinito.MenuBookmark';
import { session } from "@web/session";
import { renderToFragment } from "@web/core/utils/render";

const { fuzzyLookup } = require('@web/core/utils/search');
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { variables, colors, to_color } from './variables';

const {
    onMounted,
    onWillStart,
    useExternalListener,
    mount,
    useRef,
    useState,
    onPatched
} = owl;

// Patching the NavBar component
patch(NavBar.prototype, {

    /**
     * @override
     * Setup method to initialize the NavBar component
     */
    setup() {
        // Call the setup method of the parent class
        super.setup()
        // Deferred object for search functionality - using Promise instead of jQuery Deferred
        this._search_def = null;
        this._search_timeout = null;

        // Compute apps and menu items
        let {
            apps,
            menuItems
        } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;
        this.state = useState({
            flag: false,
        });
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
            if (dark) {
                if (!document.body.classList.contains('dark-mode')) {
                    document.body.classList.add('dark-mode');
                }
                const navbars = document.querySelectorAll('.o_navbar, .o_main_navbar, .pos-topheader');
                navbars.forEach(n => {
                    n.classList.add('dark-mode');
                });
            }
        };

        // Execute mounted logic after component is mounted
        onMounted(() => {
            // Assign DOM elements using native JavaScript
            this.$search_container = document.querySelector(".search-container");
            this.$search_input = document.querySelector(".search-input input");
            this.$search_results = document.querySelector(".search-results");
            this.$app_menu = document.querySelector(".app-menu");
            this.$dropdown_menu = document.querySelector(".dropdown-menu");
            this.doGreeting(); // Perform greeting
            this.setupSidebarListeners(); // Setup sidebar toggle listeners
            applyDarkMode();
        });

        onPatched(() => {
            applyDarkMode();
        });
    },

    // Setup sidebar toggle listeners
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

    // Method for greeting user based on current time
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
            // ✅ Fetch full session info
            const sessionInfo = await rpc('/web/session/get_session_info');
            const userName = sessionInfo.name || "User";
            const userId = sessionInfo.uid;
            const baseUrl = sessionInfo['web.base.url'] || window.location.origin;

            greetings += userName;

            // ✅ Update greeting text
            const greetingEl = document.querySelector('.infinito-greeting');
            if (greetingEl) {
                greetingEl.textContent = greetings;
            }

            // ✅ Update user image
            const imgUrl = `${baseUrl}/web/image?model=res.users&field=avatar_128&id=${userId}`;
            const userImgEl = document.querySelector('.infinito-user_img');
            if (userImgEl) {
                userImgEl.setAttribute('src', imgUrl);
            }

        } catch (error) {
            console.error("Error fetching session info:", error);
        }
    },
    // Method to search menus based on user input
    _searchMenusSchedule() {
        // Implementation of search menus
        if (this.$search_results) {
            this.$search_results.classList.remove("o_hidden");
        }
        if (this.$app_menu) {
            this.$app_menu.classList.add("o_hidden");
        }

        // Clear existing timeout
        if (this._search_timeout) {
            clearTimeout(this._search_timeout);
        }

        // Set new timeout
        this._search_timeout = setTimeout(() => {
            this._searchMenus();
        }, 50);
    },

    // Method to handle menu search
    _searchMenus() {
        // Implementation of menu search
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

                // ✅ Convert binary icon to base64 data URL
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

        const render = renderToFragment(
            "backend_theme_infinito.SearchResults", {
            results: results,
            widget: this,
        }
        );

        if (this.$search_results) {
            this.$search_results.innerHTML = "";
            this.$search_results.appendChild(render);
        }
    },

    // Method to handle click events
    onClick(ev) {
        // Implementation of click event handling
        ev.preventDefault();

        let target = ev.target;
        let data;

        // Traverse up to find the element with dataset
        while (target && !target.dataset.menuId && target !== document.body) {
            target = target.parentElement;
        }

        if (target && target.dataset) {
            data = target.dataset;
        }

        if (data && data.menuId) {
            // Get the menu item
            const menuId = parseInt(data.menuId);
            const menu = this.menuService.getMenu(menuId);

            if (menu) {
                // Navigate to the app
                this.menuService.selectMenu(menu);

                // Add to recent apps
                let app = {
                    'appId': data.menuId
                };
                rpc('/theme_studio/add_recent_app', {
                    method: 'call',
                    args: [app]
                }).catch(err => {
                    console.error('Failed to add recent app:', err);
                });
            }
        }

        // Close the sidebar
        const sidebar = document.getElementById('sidebar_panel');
        if (sidebar) {
            sidebar.classList.remove('show');
        }

        // Close any open dropdowns
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

    // Helper method to set display style
    _setElementsDisplay(selector, displayValue) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = displayValue;
            el.style.setProperty('display', displayValue, 'important');
        });
    },

    // Getters and setters for various properties
    get sidebarEnabled() {
        return session.sidebar;
    },
    set sidebarEnabled(val) {
    },
    get sidebarIcon() {
        return session.sidebarIcon;
    },
    set sidebarIcon(val) {
    },
    get sidebarName() {
        return session.sidebarName;
    },
    set sidebarName(val) {
    },
    get sidebarResize() {
        return session.sidebarIcon && !session.sidebarName ? 'm-sidebar' : ''
    },
    set sidebarResize(val) {
    },
    get sidebarCompany() {
        return session.sidebarCompany;
    },
    set sidebarCompany(val) {
    },
    get sidebarCompanyLogo() {
        return session.sidebarCompany ? 'has-company' : '';
    },
    set sidebarCompanyLogo(val) {
    },
    get sidebarUser() {
        return session.sidebarUser;
    },
    set sidebarUser(val) {
    },
    get FullScreenEnabled() {
        return session.fullscreen ? 'd-none' : '';
    },
    set FullScreenEnabled(val) {
    },
    get fullScreenApp() {
        return session.fullScreenApp;
    },
    set fullScreenApp(val) {
    },
});

// Patching the WebClient component
patch(WebClient.prototype, {
    // Setup method to initialize the WebClient component
    setup() {
        // Call the setup method of the parent class
        super.setup()
        // Attach mouse move listener
        useExternalListener(document.body, 'mousemove', this.mouseMove);
        // Execute logic on component will start
        onWillStart(this.onWillStart);
        // Execute logic after component is mounted
        onMounted(() => {
            // Mount MenuBookmark and InfinitoRecentApps components
            this.menuBookMark = mount(MenuBookmark, document.body);
            this.recent = mount(InfinitoRecentApps, document.body);
        })
    },

    // Logic executed before component starts
    async onWillStart() {
        // Implementation of onWillStart logic
        this.fullScreenEnabled = session.fullscreen;
        this.recentApps = session.recentApps;
        this.is_dark = false;

        const webClient = document.querySelector('.o_web_client');
        if (session.infinitoRtl) {
            if (webClient) webClient.classList.add('infinito-rtl');
        } else {
            if (webClient) webClient.classList.remove('infinito-rtl');
        }

        this.last_check = new Date().getMinutes();
        this.darkModeCheck();
    },

    // Method to rerender menu bookmark
    rerenderMenuBookmark() {
        // Implementation of rerendering menu bookmark
        if (this.menuBookmark && this.menuBookmark.state) {
            this.menuBookmark.state.menus = session.infinitoMenuBookmarks;
        }
    },

    // Method to handle mouse move events
    mouseMove(ev) {
        // Implementation of mouse move handling
        if (this.fullScreenEnabled && this.env.services.ui.size >= 4) {
            if (ev.clientY <= 20) {
                const actionManager = ev.target.closest('.o_action_manager');
                if (actionManager && actionManager.previousElementSibling) {
                    const nav = actionManager.previousElementSibling.querySelector('nav');
                    if (nav) nav.classList.remove('d-none');
                }
            } else {
                const actionManager = ev.target.closest('.o_action_manager');
                if (actionManager && actionManager.previousElementSibling) {
                    const nav = actionManager.previousElementSibling.querySelector('nav');
                    if (nav) nav.classList.add('d-none');
                }
            }
        }

        if (this.recentApps && this.env.services.ui.size >= 4) {
            var recentapps = document.getElementById("recentApps");
            if (ev.clientY >= (screen.availHeight - 200)) {
                if (recentapps) recentapps.classList.remove('d-none');
            } else {
                if (recentapps) recentapps.classList.add('d-none');
            }
        }

        if (session.infinitoBookmarks.length && session.infinitoBookmark && this.env.services.ui.size >= 4) {
            var Menuboook = document.getElementById("menuBookmark");
            if (ev.clientX >= (screen.availWidth - 160)) {
                if (Menuboook) Menuboook.classList.add('d-flex');
            } else {
                if (Menuboook) Menuboook.classList.remove('d-flex');
            }
        }

        let now = new Date();
        if (this.last_check != now.getMinutes()) {
            this.darkModeCheck();
            this.last_check = now.getMinutes();
        }
    },

    // Method to check dark mode
    darkModeCheck() {
        // Implementation of dark mode check
        const webClient = document.querySelector('.o_web_client');

        if (session.infinitoDark) {
            if (session.infinitoDarkMode == 'all') {
                if (webClient) webClient.classList.add('dark-mode');
                this.is_dark = true;
            } else {
                let now = new Date();
                let dark = false;
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

                if (endHour > hour && hour > startHour) {
                    dark = true;
                } else if (hour == startHour && min >= startMin && hour < endHour) {
                    dark = true;
                } else if (hour == endHour && min <= endMin && hour >= startHour) {
                    dark = true;
                } else {
                    dark = false;
                }

                if (dark) {
                    if (webClient) webClient.classList.add('dark-mode');
                    this.is_dark = true;
                } else {
                    if (webClient) webClient.classList.remove('dark-mode');
                    this.is_dark = false;
                }
            }
        } else if (!session.infinitoDark && this.is_dark) {
            if (webClient) webClient.classList.remove('dark-mode');
            this.is_dark = false;
        }
    },
});

// Patching the DropdownItem component
patch(DropdownItem.prototype, {
    // Method to handle click events
    onClick(ev) {
        // Implementation of click event handling
        super.onClick(ev);
        if (ev.target.classList.contains('o_app')) {
            let app = {
                'appId': ev.target.dataset.section
            }
            rpc('/theme_studio/add_recent_app', {
                method: 'call',
                args: [app]
            });
        }
    }
});

// Patching the ControlPanel component
patch(ControlPanel.prototype, {
    setup() {
        // Call the setup method of the parent class
        super.setup();
        // Execute logic after component is mounted
        onMounted(this.mounted.bind(this));
        // Initialize component state and reference
        this.infinitoState = useState({
            infinitoBookmarks: session.infinitoBookmarks || [],
            infinitoMenuBookmarks: session.infinitoMenuBookmarks || [],
            infinitoBookmarkColors: []
        });
        this.bookmarkRef = useRef('bookmark');
    },

    // Method to handle bookmarking
    async onBookmark(ev) {
        // Implementation of bookmarking
        let action_id = this.env.config.actionId;
        let url = location.href.split('/');
        let menu_url = url[url.length - 1];

        // Check if the action is already bookmarked
        if (!this.infinitoState.infinitoBookmarks.includes(action_id)) {
            let menu = {
                'actionId': action_id,
                'menuUrl': menu_url
            };

            const breadcrumbActive = document.querySelector('.breadcrumb-item.active');
            const breadcrumbText = breadcrumbActive ? breadcrumbActive.textContent : '';

            let book = {
                name: breadcrumbText,
                short_name: breadcrumbText.substring(0, 2).toUpperCase(),
                url: menu_url
            };

            // Add bookmark through rpc
            await rpc('/theme_studio/add_menu_bookmarks', {
                method: 'call',
                args: { menu }
            });

            // Update DOM and state dynamically
            ev.target.classList.add("active");
            ev.target.style.color = 'yellow';
            this.infinitoState.infinitoBookmarks.push(action_id);
            this.infinitoState.infinitoMenuBookmarks.push(book);
            this.infinitoState.infinitoBookmarkColors.push('yellow');
            location.reload();

        } else {
            let index = this.infinitoState.infinitoBookmarks.indexOf(action_id);
            this.infinitoState.infinitoBookmarks.splice(index, 1);
            this.infinitoState.infinitoMenuBookmarks.splice(index, 1);
            this.infinitoState.infinitoBookmarkColors.push('blue');
            let menu = {
                'actionId': action_id
            };

            // Remove bookmark through rpc
            await rpc('/theme_studio/remove_menu_bookmarks', {
                method: 'call',
                args: { menu }
            });

            // Update DOM and state dynamically
            ev.target.classList.remove("active");
            ev.target.style.color = ''; // Reset the color or apply your preferred default
        }
    },

    mounted() {
        if (this.env.config && session.infinitoBookmark) {
            let action_id = this.env.config.actionId;
            if (this.infinitoState.infinitoBookmarks.includes(action_id)) {
                if (this.bookmarkRef.el) {
                    this.bookmarkRef.el.classList.add("active");
                }
            }
        }
    },

    get bookmarkOn() {
        return session.infinitoBookmark;
    },
    set bookmarkOn(value) {
        session.bookmarkOn = value;
    }
});