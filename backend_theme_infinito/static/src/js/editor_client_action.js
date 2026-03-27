/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { EditorMenu } from "./editor_menu"
import { ThemeEditorSidebar } from "./theme_editor_sidebar"
//import { jsonrpc } from "@web/core/network/rpc_service";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ThemeStudioWidget } from "./ThemeStudioWidget";
const { onMounted, mount, useEnv } = owl
/**
 * EditorClientAction class handles client actions for theme editing.
 */
export class EditorClientAction extends Component{
     /**
     * Sets up the initial state and environment for the EditorClientAction component.
     */
    setup(){
        super.setup();
        this.env= useEnv();
        this.dialog = useService("dialog");
        this._mountedSidebar = null;
        var navbar= document.querySelector(".o_main_navbar")
        if (navbar) {
            navbar.style.display = "none";
        }
        this.state=useState({
            menus:false,
            viewType:'tree',
            sidebarOpen: false,
        })
        this.state.menus = [{
            id:1,
            name: 'Views',
            children: [{
                'name': 'Tree/List',
                'selector': 'tree',
            },
            {
                'name': 'Form',
                'selector': 'form',
            },
            {
                'name': 'Kanban',
                'selector': 'kanban',
            },
            {
                'name': 'Control Panel',
                'selector': 'control_panel',
            }],
            }, {
            id:2,
            name: 'UI Elements',
            children: [{
               'name': 'Button',
               'selector': 'button',
            },
            {
              'name': 'Progress Bar',
              'selector': 'progress_bar',
            },
            {
              'name': 'Tab',
              'selector': 'tab',
            },
            {
               'name': 'Input',
               'selector': 'input',
            },
            {
               'name': 'Search',
               'selector': 'search',
            },
            {
               'name': 'Misc',
               'selector': 'misc',
                },],
            }
    ];
    }
        /**
         * Handles button click event to switch between view types.
         * @param {Event} ev - The click event object.
         */
        _onButtonClick(ev) {
    ev.preventDefault();
    const mode = ev.currentTarget.id;

    // ✅ Close sidebar when switching UI elements
    if (this.state.sidebarOpen) {
        this._closeSidebar();
    }

    this.state.viewType = mode;
}
_closeSidebar() {
    const main_div = document.querySelector('.marg_main');
    const sidebar = document.querySelector(".sidebar_simple_editor");

    this.state.sidebarOpen = false;

    if (sidebar) {
        sidebar.remove();
    }

    if (main_div) {
        main_div.style.marginLeft = "0";
        main_div.style.width = "100%";
    }

    const hamburger = document.querySelector('.theme_studio_toggle_sidebar');
    if (hamburger) {
        hamburger.classList.remove('open');
    }
}

        /**
         * Handles item click event in the menu.
         * @param {Event} ev - The click event object.
         */
	        onItemClick(ev){
	            // Ensure we only ever have one sidebar mounted. Multiple mounts lead to overlapping DOM,
	            // flaky click targets, and performance issues.
	            try {
	                if (this._mountedSidebar?.destroy) {
	                    this._mountedSidebar.destroy();
	                }
	            } catch {
	                // ignore
	            }
	            this._mountedSidebar = null;
	            const existingSidebar = document.getElementById("theme_editor_sidebar_preset");
	            if (existingSidebar) existingSidebar.remove();

	            const targetEl = ev.currentTarget;
	            // Pass a stable reference to the selected DOM node (not the event object).
	            // Storing the event causes flaky behavior since event.currentTarget is only set during dispatch.
	            const object = { target: targetEl };
	            var elem_name = targetEl.dataset.name
	            var preset = (ev.target && ev.target.dataset && ev.target.dataset.preset) || targetEl.dataset.preset
	            var env= this.env;
	            var dialog = this.dialog;
	            ev.stopPropagation();
	            this.sidebar_pos = document.querySelector('.backend_theme_studio_sidebar .sidebar-here')
	            var sidebars=document.querySelector('.marg_main')
            if (sidebars){
                sidebars.style.marginLeft="340px";
            }else{
                sidebars.style.marginLeft="0px";
            }
	            // `mount` returns the mounted component (or a promise of it, depending on Owl build).
	            const mounted = mount(ThemeEditorSidebar, document.body, { env, dialog, props: { elem_name, preset, object } });
	            if (mounted && typeof mounted.then === "function") {
	                mounted.then((inst) => (this._mountedSidebar = inst));
	            } else {
	                this._mountedSidebar = mounted;
	            }
	        }
        /**
         * Handles the event when the theme studio sidebar is closed.
         * @param {Event} ev - The click event object.
         */
        _onThemeStudioClose(ev){
            ev.preventDefault();
            window.location.href = '/web'
        }
         /**
         * Handles the event when the reset button is clicked to reset to default settings.
         * @param {Event} ev - The click event object.
         */
        _onResetClick(ev){
             rpc('/theme_studio/reset_to_default',  {
                method:'call',
            });
            this.setAssets();
            location.reload();
        }
         /**
         * Toggles the sidebar visibility.
         * @param {Event} ev - The click event object.
         */
        _onThemeStudioToggleSidebar (ev) {
           ev.currentTarget.classList.toggle('open');
           var main_div = document.querySelector('.marg_main');
           this.state.sidebarOpen = !this.state.sidebarOpen;
           ev.preventDefault();
           if (main_div) {
    if (this.state.sidebarOpen) {
        mount(EditorMenu, document.body);
        main_div.style.marginLeft = "340px";
        main_div.style.width = "calc(100% - 340px)";
    } else {

        main_div.style.marginLeft = "0";
        document.querySelector(".sidebar_simple_editor").remove();
        main_div.style.width = "100%";
    }
}

        }
        /**
         * Sets the assets for the theme editor.
         */
        setAssets(){
            location.search = "?debug=assets";
        }
}
// Define the template for the EditorClientAction component
EditorClientAction.template = "backend_theme_infinito.ThemeStudioMenu";

// Register the EditorClientAction component in the actions registry
registry.category("actions").add("backend_theme_infinito.editor_client_action",EditorClientAction);
