/** @odoo-module **/
/*
 * Variant of the standard Reference field for a Reference whose `selection`
 * only ever lists one target model (e.g. doctor_member_ref, which is kept as
 * a Reference rather than a Many2one purely so this module doesn't hard-
 * depend on odoo_nhs_training).
 *
 * The stock widget always shows a model-type <select> first and only reveals
 * the record search box once that select fires an onChange - even when it
 * has a single, forced option, which reads as a dead-end dropdown ("only
 * option is the field's own label"). Here the model is resolved
 * automatically from the field's own selection, so the record search box is
 * shown straight away.
 */
import { registry } from "@web/core/registry";
import { referenceField, ReferenceField } from "@web/views/fields/reference/reference_field";

export class SingleModelReferenceField extends ReferenceField {
    /** Never show the model-type <select> - there is only ever one target model. */
    get hideModelSelector() {
        return true;
    }

    getRelation() {
        const relation = super.getRelation();
        if (relation) {
            return relation;
        }
        const [onlyOption] = this.props.record.fields[this.props.name].selection || [];
        return onlyOption ? onlyOption[0] : undefined;
    }
}

export const singleModelReferenceField = {
    ...referenceField,
    component: SingleModelReferenceField,
};

registry.category("fields").add("reference_single", singleModelReferenceField);
