import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { groupBy } from "@web/core/utils/arrays";

export class Partner extends DynamicSnippet {
    // While the selector has 'upcoming_snippet' in its name, it now has a filter
    // option to include ongoing events. The name is kept for backward compatibility.
    static selector = ".s_partner_upcoming_snippet";



}



