/** @odoo-module **/

const { useRef, onWillStart, xml ,onMounted} = owl;
import { rpc } from "@web/core/network/rpc";


export default class InfinitoRecentApps extends owl.Component {
    setup(){
        super.setup();
        this.ref = useRef('recentApps');
        onWillStart(this.willStart);
        onMounted(this.mounted)
    }
    async willStart(){
        // Retrieve recent apps data from the server
        await rpc('/theme_studio/get_recent_apps', {
            method: 'call',
        }).then(data => this.recent_app = data);
    }
    get recentApps(){
        return this.recent_app;
    }
    mounted(){
        this.dragElement(this.__owl__.refs.recentApps, 'x');
    }
}
InfinitoRecentApps.template = xml`
<div class="recent-apps d-none" id="recentApps" t-ref="recentApps">
        <div class="icon-tray">
         <t t-foreach="recentApps" t-as="app" t-key="app">
            <a class="icon" t-on-click="() => openApp(app)">
              <div class="img_wrapper">
                <img t-if="app.type=='svg'" class="sidebar_img" t-attf-src="data:image/svg+xml;base64,{{app.icon}}" width="40px" height="40px"/>
                <img  t-if="app.type=='png'" class="sidebar_img" t-attf-src="data:image/png;base64,{{app.icon}}" width="40px" height="40px"/>
              </div>
              <span class="zoomIn" t-esc="app.name"/>
            </a>
         </t>
        </div>
      </div>
`;