/** @odoo-module **/
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

const { onMounted, useState, useRef } = owl;

patch(ControlPanel.prototype, {

    setup() {
        super.setup();
        onMounted(this.mounted.bind(this));
        this.infinitoState = useState({
            infinitoBookmarks: session.infinitoBookmarks || [],
            infinitoMenuBookmarks: session.infinitoMenuBookmarks || [],
            // Pre-fill blue for every already-bookmarked action so the icon
            // renders blue on first mount without needing a click.
            infinitoBookmarkColors: (session.infinitoBookmarks || []).map(() => '#4f6bf8'),
        });
        this.bookmarkRef = useRef('bookmark');
    },

    async onBookmark(ev) {
        let action_id = this.env.config.actionId;
        // Store the full pathname so the bookmark link navigates correctly.
        // e.g. /odoo/sales/products  (not just "products" which gives a 404)
        let menu_url = location.pathname;

        if (!this.infinitoState.infinitoBookmarks.includes(action_id)) {
            let menu = { 'actionId': action_id, 'menuUrl': menu_url };

            const breadcrumbActive = document.querySelector('.breadcrumb-item.active');
            const breadcrumbText = breadcrumbActive ? breadcrumbActive.textContent : '';

            let book = {
                name: breadcrumbText,
                short_name: breadcrumbText.substring(0, 2).toUpperCase(),
                url: menu_url
            };

            await rpc('/theme_studio/add_menu_bookmarks', {
                method: 'call',
                args: { menu }
            });

            ev.target.classList.add("active");
            ev.target.style.color = '#4f6bf8';
            this.infinitoState.infinitoBookmarks.push(action_id);
            this.infinitoState.infinitoMenuBookmarks.push(book);
            this.infinitoState.infinitoBookmarkColors.push('#4f6bf8');
            location.reload();
        } else {
            let index = this.infinitoState.infinitoBookmarks.indexOf(action_id);
            this.infinitoState.infinitoBookmarks.splice(index, 1);
            this.infinitoState.infinitoMenuBookmarks.splice(index, 1);
            this.infinitoState.infinitoBookmarkColors.push('blue');
            let menu = { 'actionId': action_id };

            await rpc('/theme_studio/remove_menu_bookmarks', {
                method: 'call',
                args: { menu }
            });

            ev.target.classList.remove("active");
            ev.target.style.color = '';
        }
    },

    mounted() {
        if (this.env.config && session.infinitoBookmark) {
            let action_id = this.env.config.actionId;
            let idx = this.infinitoState.infinitoBookmarks.indexOf(action_id);
            if (idx !== -1) {
                if (this.bookmarkRef.el) {
                    this.bookmarkRef.el.classList.add("active");
                    this.bookmarkRef.el.style.color = '#4f6bf8';
                }
                // Ensure the reactive color array has the blue value at this index
                this.infinitoState.infinitoBookmarkColors[idx] = '#4f6bf8';
            }
        }
    },

    get bookmarkOn() { return session.infinitoBookmark; },
    set bookmarkOn(value) { session.bookmarkOn = value; },
});
