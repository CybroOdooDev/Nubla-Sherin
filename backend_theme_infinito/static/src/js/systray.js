/* @odoo-module */
import { Component,useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Counter } from "./editor_menu"
const {  mount,useEnv } = owl
export class InfinitoSystrayItem extends Component{
    static template="backend_theme_infinito.StudioSystray"
    setup(){
        this.render();
        this.env= useEnv();
        this.action = useService("action");
        this.actionService = useService("action");
        this.mode = false;
        this.editor = useService("editor");
    }
     /**
     * Method to handle click event for Simple Editor
     */
    _onClickSimpleEditor(){
         var $el = $('body')
    }
     /**
     * Method to handle click event for Advanced Editor
     */
    _onClickAdvancedEditor(){
          var navbar= document.querySelector(".o_main_navbar")
          if (navbar) {
            navbar.style.display = "none";
            this.editor.open();
          }
    }
}
// Exporting systrayItem
export const systrayItem = {
    Component: InfinitoSystrayItem,
};
// Definition of InfinitoSystrayAdv component
export class InfinitoSystrayAdv extends Component{
    static template="backend_theme_infinito.AdvSystray"
     // Setup method to initialize component
    setup(){
        this.env= useEnv();
        this.action = useService("action");
        this.dialog = useService("dialog");
    }
     /**
     * Method to handle click event for Advanced Systray
     */


_onClick() {
    const env = this.env;
    const dialog = this.dialog;

    const main = document.querySelector('.o_action_manager');
    const existingSidebar = document.querySelector('.sidebar_simple_editor');

    if (existingSidebar) {
        return;
    }

    mount(Counter, document.body, { env, dialog });

    if (main) {
        main.classList.add('infinito-sidebar-open');
    }
}

}
export const InfinitoSystrayAdvItem={
    Component: InfinitoSystrayAdv,
};
registry.category("systray").add("backend_theme_infinito.infinito_systray",systrayItem, {sequence:25})
                            .add("backend_theme_infinito.infinito_systray_adv",InfinitoSystrayAdvItem,{sequence:26})
