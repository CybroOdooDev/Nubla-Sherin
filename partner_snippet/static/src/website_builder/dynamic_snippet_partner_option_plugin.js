import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class DynamicSnippetEventsOptionPlugin extends Plugin {

    static dependencies = ["dynamicSnippetOption"];
    modelNameFilter = "res.partner";

    resources = {
        builder_options: {
            props: {
                modelNameFilter: this.modelNameFilter,
            },
        }),


}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);